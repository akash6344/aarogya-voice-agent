'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  BarVisualizer,
  LiveKitRoom,
  RoomAudioRenderer,
  useVoiceAssistant,
} from '@livekit/components-react';
import '@livekit/components-styles';
import { AudioLines, HeartPulse, Mic, PhoneOff, ShieldCheck } from 'lucide-react';
import {
  COPY,
  LANGUAGE_LABELS,
  RECOMMENDED_STT,
  STT_PROVIDER_LABELS,
  STT_PROVIDERS,
  type Language,
  type SttProvider,
} from '@/lib/config';

type ConnectionDetails = {
  serverUrl: string;
  roomName: string;
  participantToken: string;
};

type Copy = (typeof COPY)[Language];

function AssistantPanel({ copy, onEnd }: { copy: Copy; onEnd: () => void }) {
  const { state, audioTrack } = useVoiceAssistant();

  const status =
    state === 'listening'
      ? copy.listening
      : state === 'thinking'
        ? copy.thinking
        : state === 'speaking'
          ? copy.speaking
          : copy.idle;

  return (
    <div className="call-panel">
      <div className="status-row">
        <Mic size={18} />
        <span>{status}</span>
      </div>
      {audioTrack && <BarVisualizer trackRef={audioTrack} barCount={5} className="visualizer" />}
      <button className="end-button" onClick={onEnd}>
        <PhoneOff size={18} />
        {copy.end}
      </button>
    </div>
  );
}

export function VoiceAssistant() {
  const [language, setLanguage] = useState<Language>('en');
  const [stt, setStt] = useState<SttProvider>(RECOMMENDED_STT.en);
  const [sttTouched, setSttTouched] = useState(false);
  const [connection, setConnection] = useState<ConnectionDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const copy = COPY[language];

  const selectLanguage = useCallback(
    (code: Language) => {
      setLanguage(code);
      if (!sttTouched) {
        setStt(RECOMMENDED_STT[code]);
      }
    },
    [sttTouched],
  );

  const endCall = useCallback(() => {
    setConnection(null);
    setLoading(false);
  }, []);

  const startCall = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/livekit-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language, stt }),
      });
      if (!response.ok) {
        throw new Error(copy.error);
      }
      const details = (await response.json()) as ConnectionDetails;
      setConnection(details);
    } catch {
      setError(copy.error);
    } finally {
      setLoading(false);
    }
  }, [copy.error, language, stt]);

  useEffect(() => {
    if (!connection) {
      return;
    }
    const timer = window.setTimeout(endCall, 5 * 60 * 1000);
    return () => window.clearTimeout(timer);
  }, [connection, endCall]);

  return (
    <div className="page">
      <nav>
        <div className="brand">
          <HeartPulse size={22} />
          Aarogya
        </div>
        <div className="secure">
          <ShieldCheck size={16} />
          Secure voice demo
        </div>
      </nav>

      <main className="hero">
        <div className="hero-inner">
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>

          {connection ? (
            <LiveKitRoom
              serverUrl={connection.serverUrl}
              token={connection.participantToken}
              connect
              audio
              onDisconnected={endCall}
            >
              <AssistantPanel copy={copy} onEnd={endCall} />
              <RoomAudioRenderer />
            </LiveKitRoom>
          ) : (
            <div className="start-card">
              <fieldset disabled={loading}>
                <legend>{copy.langLegend}</legend>
                <div className="languages">
                  {(Object.keys(LANGUAGE_LABELS) as Language[]).map((code) => (
                    <button
                      key={code}
                      className={language === code ? 'selected' : ''}
                      onClick={() => selectLanguage(code)}
                    >
                      <span>{LANGUAGE_LABELS[code].native}</span>
                      <small>{LANGUAGE_LABELS[code].label}</small>
                    </button>
                  ))}
                </div>
              </fieldset>

              <fieldset disabled={loading}>
                <legend>{copy.sttLegend}</legend>
                <div className="providers">
                  {STT_PROVIDERS.map((code) => (
                    <button
                      key={code}
                      className={stt === code ? 'selected' : ''}
                      onClick={() => {
                        setStt(code);
                        setSttTouched(true);
                      }}
                    >
                      <span>{STT_PROVIDER_LABELS[code].label}</span>
                      <small>{STT_PROVIDER_LABELS[code].note}</small>
                    </button>
                  ))}
                </div>
              </fieldset>

              <button className="start-button" onClick={startCall} disabled={loading}>
                <AudioLines size={18} />
                {loading ? copy.connecting : copy.start}
              </button>

              {error && <p className="error">{error}</p>}
            </div>
          )}

          <p className="privacy">
            <ShieldCheck size={14} />
            {copy.privacy}
          </p>
        </div>
      </main>

      <footer>
        <span>English · Hindi · Telugu</span>
        <span>LiveKit voice agent</span>
      </footer>
    </div>
  );
}
