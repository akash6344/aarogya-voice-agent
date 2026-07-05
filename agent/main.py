"""Aarogya voice medical-appointment agent (LiveKit Agents).

Voice loop: LiveKit audio -> VAD -> STT (user-selected) -> LLM + clinic tools
-> per-language TTS -> playback -> continue listening, with turn detection, noise
cancellation, and barge-in.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

from livekit.agents import (  # noqa: E402
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import noise_cancellation, silero  # noqa: E402
from livekit.plugins.turn_detector.multilingual import MultilingualModel  # noqa: E402

from clinic.availability import combine, parse_date, parse_time  # noqa: E402
from clinic.db import Database  # noqa: E402
from clinic.models import BookingError, Clinic, SlotTakenError  # noqa: E402
from clinic.prompts import (  # noqa: E402
    MISSING_INFO,
    NO_CLINIC_DATA,
    build_instructions,
    greeting,
)
from clinic.providers import build_llm, build_stt, build_tts, llm_mode_label  # noqa: E402
from clinic.validators import (  # noqa: E402
    normalize_specialty_query,
    patient_name_ok,
    patient_phone_ok,
)

logger = logging.getLogger("aarogya-agent")

SUPPORTED_LANGUAGES = ("en", "hi", "te")


def _clinic_timezone(clinic: Clinic | None) -> ZoneInfo:
    tz_name = (clinic.timezone if clinic else None) or os.environ.get(
        "CLINIC_TIMEZONE", "Asia/Kolkata"
    )
    return ZoneInfo(tz_name)


def _clinic_summary(clinic: Clinic, tz: ZoneInfo) -> str:
    return (
        f"Clinic: {clinic.name}. "
        f"Hours: {clinic.opening_time.strftime('%H:%M')}–{clinic.closing_time.strftime('%H:%M')} "
        f"({tz.key}). Appointment length: {clinic.slot_minutes} minutes. "
        f"Phone: {clinic.phone or 'not listed'}. Address: {clinic.address or 'not listed'}."
    )


class ClinicAgent(Agent):
    def __init__(self, *, language: str, db: Database, clinic: Clinic, tz: ZoneInfo) -> None:
        now = datetime.now(tz)
        super().__init__(
            instructions=build_instructions(
                language=language,
                now_str=now.strftime("%A, %d %B %Y, %H:%M"),
                clinic_summary=_clinic_summary(clinic, tz),
            )
        )
        self.language = language
        self.db = db
        self.clinic = clinic
        self.tz = tz

    def _missing(self) -> str:
        return MISSING_INFO.get(self.language, MISSING_INFO["en"])

    def _now(self) -> datetime:
        return datetime.now(self.tz)

    def _fmt_time(self, dt: datetime) -> str:
        return dt.astimezone(self.tz).strftime("%H:%M")

    def _fmt_date(self, d: date) -> str:
        return d.strftime("%A, %d %B %Y")

    # ---- tools -------------------------------------------------------------

    @function_tool()
    async def list_specialties(self, context: RunContext) -> str:
        """List all medical specialties at the clinic. Call when the patient does not know
        which department they need, or asks what services are available."""
        specialties = await self.db.list_specialties()
        if not specialties:
            return self._missing()
        names = [s.name for s in specialties]
        return f"Available specialties: {', '.join(names)}."

    @function_tool()
    async def find_doctors(
        self, context: RunContext, specialty: str = "", doctor_name: str = ""
    ) -> str:
        """Find doctors by specialty and/or name. ALWAYS call when a specialty is mentioned
        or the patient asks who is available. Read the returned doctor name(s) aloud and
        ask which doctor they prefer before checking availability."""
        query_specialty = normalize_specialty_query(specialty) if specialty else ""
        doctors = await self.db.find_doctors(
            specialty=query_specialty or None, name=doctor_name or None
        )
        if not doctors:
            if query_specialty or specialty:
                available = await self.db.list_specialties()
                names = ", ".join(s.name for s in available)
                label = specialty or query_specialty
                return (
                    f"No {label} doctor at this clinic. "
                    f"Available specialties: {names}."
                )
            return self._missing()
        if len(doctors) == 1:
            d = doctors[0]
            qual = f", {d.qualifications}" if d.qualifications else ""
            langs = f". Speaks {', '.join(d.languages)}" if d.languages else ""
            return f"For {d.specialty} we have {d.name}{qual}{langs}."
        parts = []
        for d in doctors:
            qual = f" ({d.qualifications})" if d.qualifications else ""
            langs = f", speaks {', '.join(d.languages)}" if d.languages else ""
            parts.append(f"{d.name} — {d.specialty}{qual}{langs}")
        return f"Doctors: {'; '.join(parts)}."

    @function_tool()
    async def check_availability(
        self, context: RunContext, on_date: str, doctor_name: str = "", specialty: str = ""
    ) -> str:
        """Check open appointment slots on a date (YYYY-MM-DD). Call ONLY after the patient
        has chosen a doctor and date. Prefer passing doctor_name. Read times aloud and ask
        which slot they want."""
        try:
            target = parse_date(on_date)
        except ValueError:
            return "Please tell me the date again, for example the 5th of July."
        if not (doctor_name or specialty):
            return "Need a doctor or specialty before checking slots."

        query_specialty = normalize_specialty_query(specialty) if specialty else ""
        doctors = await self.db.find_doctors(
            specialty=query_specialty or None, name=doctor_name or None
        )
        if not doctors:
            if query_specialty or specialty:
                available = await self.db.list_specialties()
                names = ", ".join(s.name for s in available)
                return f"No matching doctor. Available specialties: {names}."
            return self._missing()

        if len(doctors) > 1 and not doctor_name:
            names = ", ".join(d.name for d in doctors)
            return f"Multiple doctors: {names}."

        if target.weekday() == 6:
            return f"The clinic is closed on Sundays."

        lines: list[str] = []
        for doctor in doctors[:1]:
            slots = await self.db.available_slots(
                doctor=doctor,
                on_date=target,
                tz=self.tz,
                slot_minutes=self.clinic.slot_minutes,
                now=self._now(),
            )
            if slots:
                times = ", ".join(self._fmt_time(s.starts_at) for s in slots[:8])
                lines.append(f"{doctor.name} on {self._fmt_date(target)}: {times}")
            else:
                lines.append(f"{doctor.name} on {self._fmt_date(target)}: no open slots")
        return " | ".join(lines)

    @function_tool()
    async def book_appointment(
        self,
        context: RunContext,
        doctor_name: str,
        on_date: str,
        at_time: str,
        patient_name: str,
        phone: str,
    ) -> str:
        """Book an appointment. Requires patient name and phone from the caller. Only call AFTER verbal yes."""
        ok, msg = patient_name_ok(patient_name)
        if not ok:
            return msg
        ok, msg = patient_phone_ok(phone, clinic_phone=self.clinic.phone)
        if not ok:
            return msg

        try:
            target_date = parse_date(on_date)
            target_time = parse_time(at_time)
        except ValueError:
            return "I didn't catch the date or time clearly. Could you repeat it?"

        if target_date.weekday() == 6:
            return "The clinic is closed on Sundays. Please choose a weekday."

        doctors = await self.db.find_doctors(name=doctor_name)
        if not doctors:
            return self._missing()
        doctor = doctors[0]

        requested = combine(target_date, target_time, self.tz)
        slots = await self.db.available_slots(
            doctor=doctor,
            on_date=target_date,
            tz=self.tz,
            slot_minutes=self.clinic.slot_minutes,
            now=self._now(),
        )
        match = next((s for s in slots if s.starts_at == requested), None)
        if match is None:
            if slots:
                times = ", ".join(self._fmt_time(s.starts_at) for s in slots[:6])
                return f"That time isn't available. Open times for {doctor.name}: {times}"
            return f"{doctor.name} has no open slots on {self._fmt_date(target_date)}."

        try:
            appt = await self.db.book(
                clinic=self.clinic,
                doctor=doctor,
                starts_at=match.starts_at,
                ends_at=match.ends_at,
                patient_name=patient_name,
                phone=phone,
                language=self.language,
            )
        except SlotTakenError:
            return "Sorry, that slot was just taken. Shall I look for another time?"
        except BookingError as exc:
            return str(exc)

        return (
            f"Booked. Doctor {appt.doctor_name}, {self._fmt_date(target_date)} at "
            f"{self._fmt_time(appt.starts_at)}, for {appt.patient_name}. "
            f"Booking reference: {appt.booking_reference}."
        )

    @function_tool()
    async def lookup_appointment(
        self, context: RunContext, booking_reference: str, phone: str
    ) -> str:
        """Look up an appointment using its booking reference and the phone number on file."""
        appt = await self.db.find_appointment(reference=booking_reference, phone=phone)
        if appt is None:
            return "I couldn't find an appointment with that reference and phone number."
        return (
            f"{appt.status.title()} appointment with {appt.doctor_name} "
            f"({appt.specialty}) on {self._fmt_date(appt.starts_at.astimezone(self.tz).date())} "
            f"at {self._fmt_time(appt.starts_at)} for {appt.patient_name}."
        )

    @function_tool()
    async def cancel_appointment(
        self, context: RunContext, booking_reference: str, phone: str
    ) -> str:
        """Cancel an appointment. Confirm with the patient before calling this."""
        appt = await self.db.cancel(reference=booking_reference, phone=phone)
        if appt is None:
            return "I couldn't find an appointment with that reference and phone number."
        if appt.status != "cancelled":
            return "That appointment is not active, so there's nothing to cancel."
        return f"Cancelled the appointment with {appt.doctor_name}, reference {appt.booking_reference}."

    @function_tool()
    async def reschedule_appointment(
        self,
        context: RunContext,
        booking_reference: str,
        phone: str,
        on_date: str,
        at_time: str,
    ) -> str:
        """Reschedule an appointment to a new date/time. Confirm the new time before calling."""
        try:
            target_date = parse_date(on_date)
            target_time = parse_time(at_time)
        except ValueError:
            return "I didn't catch the new date or time clearly. Could you repeat it?"

        appt = await self.db.find_appointment(reference=booking_reference, phone=phone)
        if appt is None:
            return "I couldn't find an appointment with that reference and phone number."

        doctors = await self.db.find_doctors(name=appt.doctor_name)
        if not doctors:
            return self._missing()
        doctor = doctors[0]

        requested = combine(target_date, target_time, self.tz)
        slots = await self.db.available_slots(
            doctor=doctor,
            on_date=target_date,
            tz=self.tz,
            slot_minutes=self.clinic.slot_minutes,
            now=self._now(),
        )
        match = next((s for s in slots if s.starts_at == requested), None)
        if match is None:
            if slots:
                times = ", ".join(self._fmt_time(s.starts_at) for s in slots[:6])
                return f"That time isn't available. Open times for {doctor.name}: {times}"
            return f"{doctor.name} has no open slots on {self._fmt_date(target_date)}."

        try:
            updated = await self.db.reschedule(
                reference=booking_reference,
                phone=phone,
                starts_at=match.starts_at,
                ends_at=match.ends_at,
            )
        except SlotTakenError:
            return "Sorry, that slot was just taken. Shall I look for another time?"
        except BookingError as exc:
            return str(exc)

        return (
            f"Rescheduled to {self._fmt_date(target_date)} at {self._fmt_time(updated.starts_at)} "
            f"with {updated.doctor_name}. Reference {updated.booking_reference}."
        )

    @function_tool()
    async def clinic_information(self, context: RunContext) -> str:
        """Return clinic name, working hours, phone, and address."""
        c = self.clinic
        return (
            f"{c.name}. Open {c.opening_time.strftime('%H:%M')} to {c.closing_time.strftime('%H:%M')}. "
            f"Phone {c.phone or 'not listed'}. Address {c.address or 'not listed'}."
        )


def _read_participant_config(metadata: str | None) -> tuple[str, str]:
    language, provider = "en", os.environ.get("DEFAULT_STT_PROVIDER", "deepgram")
    if metadata:
        try:
            data = json.loads(metadata)
            if data.get("language") in SUPPORTED_LANGUAGES:
                language = data["language"]
            if data.get("stt"):
                provider = str(data["stt"]).lower()
        except json.JSONDecodeError:
            logger.warning("Could not parse participant metadata: %r", metadata)
    return language, provider


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()
    participant = await ctx.wait_for_participant()
    language, stt_provider = _read_participant_config(participant.metadata)
    logger.info("Call started: language=%s stt=%s llm=%s", language, stt_provider, llm_mode_label())

    db = Database(os.environ["DATABASE_URL"])
    await db.connect()
    ctx.add_shutdown_callback(db.close)

    clinic = await db.get_clinic()
    tz = _clinic_timezone(clinic)

    session = AgentSession(
        stt=build_stt(stt_provider, language),
        llm=build_llm(),
        tts=build_tts(language),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        min_interruption_duration=0.4,
    )

    if clinic is None:
        # No clinic data configured: still open audio, speak the mandated phrase, and stop.
        bare = Agent(instructions="You are a receptionist. Say only the provided message.")
        await session.start(agent=bare, room=ctx.room,
                            room_input_options=RoomInputOptions(
                                noise_cancellation=noise_cancellation.BVC()))
        await session.say(NO_CLINIC_DATA.get(language, NO_CLINIC_DATA["en"]))
        return

    agent = ClinicAgent(language=language, db=db, clinic=clinic, tz=tz)
    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )
    await session.say(greeting(language, clinic.name), allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
