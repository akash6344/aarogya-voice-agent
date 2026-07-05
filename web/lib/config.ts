export const SUPPORTED_LANGUAGES = ['en', 'hi', 'te'] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

export const LANGUAGE_LABELS: Record<Language, { label: string; native: string }> = {
  en: { label: 'English', native: 'English' },
  hi: { label: 'Hindi', native: 'हिन्दी' },
  te: { label: 'Telugu', native: 'తెలుగు' },
};

export const STT_PROVIDERS = ['deepgram', 'sarvam', 'elevenlabs'] as const;
export type SttProvider = (typeof STT_PROVIDERS)[number];

export const STT_PROVIDER_LABELS: Record<SttProvider, { label: string; note: string }> = {
  deepgram: { label: 'Deepgram', note: 'Best for English' },
  sarvam: { label: 'Sarvam AI', note: 'Best for Hindi & Telugu' },
  elevenlabs: { label: 'ElevenLabs', note: 'Multilingual' },
};

export const RECOMMENDED_STT: Record<Language, SttProvider> = {
  en: 'deepgram',
  hi: 'sarvam',
  te: 'sarvam',
};

export const COPY: Record<
  Language,
  {
    title: string;
    subtitle: string;
    start: string;
    end: string;
    idle: string;
    connecting: string;
    listening: string;
    thinking: string;
    speaking: string;
    error: string;
    privacy: string;
    langLegend: string;
    sttLegend: string;
  }
> = {
  en: {
    title: 'Aarogya Voice Assistant',
    subtitle: 'Book medical appointments by voice.',
    start: 'Start voice call',
    end: 'End call',
    idle: 'Ready to help',
    connecting: 'Connecting',
    listening: 'Listening',
    thinking: 'Checking clinic information',
    speaking: 'Assistant is speaking',
    error: 'The call could not start. Check microphone access and try again.',
    privacy: 'Demo only. Do not share sensitive medical information.',
    langLegend: 'Choose your language',
    sttLegend: 'Speech recognition engine',
  },
  hi: {
    title: 'आरोग्य वॉइस असिस्टेंट',
    subtitle: 'आवाज़ से चिकित्सा अपॉइंटमेंट बुक करें।',
    start: 'वॉइस कॉल शुरू करें',
    end: 'कॉल समाप्त करें',
    idle: 'मदद के लिए तैयार',
    connecting: 'कनेक्ट हो रहा है',
    listening: 'सुन रहा है',
    thinking: 'क्लिनिक जानकारी जांच रहा है',
    speaking: 'सहायक बोल रहा है',
    error: 'कॉल शुरू नहीं हुई। माइक्रोफ़ोन अनुमति जांचें।',
    privacy: 'यह डेमो है। संवेदनशील चिकित्सा जानकारी साझा न करें।',
    langLegend: 'अपनी भाषा चुनें',
    sttLegend: 'वाक् पहचान इंजन',
  },
  te: {
    title: 'ఆరోగ్య వాయిస్ అసిస్టెంట్',
    subtitle: 'వాయిస్ ద్వారా వైద్య అపాయింట్‌మెంట్లు బుక్ చేయండి.',
    start: 'వాయిస్ కాల్ ప్రారంభించండి',
    end: 'కాల్ ముగించండి',
    idle: 'సహాయానికి సిద్ధం',
    connecting: 'కనెక్ట్ అవుతోంది',
    listening: 'వింటోంది',
    thinking: 'క్లినిక్ సమాచారాన్ని తనిఖీ చేస్తోంది',
    speaking: 'అసిస్టెంట్ మాట్లాడుతోంది',
    error: 'కాల్ ప్రారంభం కాలేదు. మైక్రోఫోన్ అనుమతిని తనిఖీ చేయండి.',
    privacy: 'ఇది డెమో మాత్రమే. సున్నితమైన వైద్య సమాచారాన్ని పంచుకోవద్దు.',
    langLegend: 'మీ భాషను ఎంచుకోండి',
    sttLegend: 'వాక్ గుర్తింపు ఇంజిన్',
  },
};
