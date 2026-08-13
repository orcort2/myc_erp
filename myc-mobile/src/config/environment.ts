import Constants from 'expo-constants';

const developmentHost = Constants.expoConfig?.hostUri?.split(':')[0];

export const API_BASE_URL = (
  process.env.EXPO_PUBLIC_API_URL ??
  (developmentHost ? `http://${developmentHost}:8000/api` : 'http://127.0.0.1:8000/api')
).replace(/\/$/, '');
