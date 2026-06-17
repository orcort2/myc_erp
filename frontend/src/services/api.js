const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api';

export async function getModules() {
  const response = await fetch(`${API_URL}/modules`);
  if (!response.ok) {
    throw new Error('No se pudieron cargar los modulos');
  }
  return response.json();
}

