import * as FileSystem from 'expo-file-system/legacy';
import { ImageManipulator, SaveFormat, type ImageRef } from 'expo-image-manipulator';
import * as ImagePicker from 'expo-image-picker';

import {
  createEvidenceMediaProvider,
  type EvidenceImagePipelineDeps,
} from '@/src/services/technical-report-image-pipeline';
import type { EvidenceMediaProvider } from '@/src/services/technical-report-media';

/**
 * Adaptador real de cámara/galería (expo-image-picker) y procesamiento
 * (expo-image-manipulator). Es la ÚNICA pieza que toca esos módulos nativos;
 * la lógica vive en technical-report-image-pipeline.ts y se prueba con
 * dependencias falsas. Requiere un build nativo con ambos módulos.
 */

const pipelineDeps: EvidenceImagePipelineDeps<ImageRef> = {
  async requestPermission(source) {
    const result = source === 'camera'
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    return { granted: result.granted };
  },
  async pick(source) {
    // quality 1: la compresión la decide la política única, no el selector.
    const options: ImagePicker.ImagePickerOptions = {
      mediaTypes: ['images'],
      allowsEditing: false,
      allowsMultipleSelection: false,
      exif: false,
      base64: false,
      quality: 1,
    };
    const result = source === 'camera'
      ? await ImagePicker.launchCameraAsync(options)
      : await ImagePicker.launchImageLibraryAsync(options);
    const asset = result.canceled ? undefined : result.assets[0];
    return asset ? { uri: asset.uri } : null;
  },
  // renderAsync aplica la orientación EXIF: el archivo final no depende de ella.
  load: (uri) => ImageManipulator.manipulate(uri).renderAsync(),
  resize: (image, size) => ImageManipulator.manipulate(image).resize(size).renderAsync(),
  saveJpeg: async (image, quality) => {
    const saved = await image.saveAsync({ format: SaveFormat.JPEG, compress: quality });
    return { uri: saved.uri, width: saved.width, height: saved.height };
  },
  async fileSize(uri) {
    const info = await FileSystem.getInfoAsync(uri);
    return info.exists && typeof info.size === 'number' ? info.size : null;
  },
  fileName: () => `evidencia-${Date.now()}.jpg`,
};

export const expoEvidenceMediaProvider: EvidenceMediaProvider = createEvidenceMediaProvider(pipelineDeps);
