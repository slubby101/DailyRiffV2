import { Audio } from "expo-av";
import * as FileSystem from "expo-file-system";
import { requestUploadUrl } from "./api";
import { useSessionStore } from "../stores/sessionStore";

const CHUNK_SIZE = 5 * 1024 * 1024; // 5 MB chunks

export interface RecordingSession {
  recording: Audio.Recording;
  startTime: number;
}

export async function startRecording(): Promise<RecordingSession> {
  const permission = await Audio.requestPermissionsAsync();
  if (!permission.granted) {
    throw new Error("Microphone permission not granted");
  }

  await Audio.setAudioModeAsync({
    allowsRecordingIOS: true,
    playsInSilentModeIOS: true,
  });

  const { recording } = await Audio.Recording.createAsync(
    Audio.RecordingOptionsPresets.HIGH_QUALITY,
  );

  return { recording, startTime: Date.now() };
}

export async function stopRecording(
  session: RecordingSession,
): Promise<{ uri: string; durationSeconds: number }> {
  await session.recording.stopAndUnloadAsync();
  await Audio.setAudioModeAsync({ allowsRecordingIOS: false });

  const uri = session.recording.getURI();
  if (!uri) {
    throw new Error("Recording URI not available");
  }

  const durationSeconds = Math.round((Date.now() - session.startTime) / 1000);
  return { uri, durationSeconds };
}

export async function uploadRecording(
  localUri: string,
  studioId: string,
  assignmentId: string,
  durationSeconds: number,
): Promise<string> {
  const { upload_url, recording_id } = await requestUploadUrl(
    studioId,
    assignmentId,
    durationSeconds,
  );

  const fileInfo = await FileSystem.getInfoAsync(localUri);
  if (!fileInfo.exists) {
    throw new Error("Recording file not found");
  }

  const totalSize = fileInfo.size;

  if (totalSize <= CHUNK_SIZE) {
    // Single-part upload for small files
    await FileSystem.uploadAsync(upload_url, localUri, {
      httpMethod: "PUT",
      headers: { "Content-Type": "audio/mp4" },
      uploadType: FileSystem.FileSystemUploadType.BINARY_CONTENT,
    });
  } else {
    // Chunked upload for larger files
    let offset = 0;
    while (offset < totalSize) {
      const length = Math.min(CHUNK_SIZE, totalSize - offset);
      const chunk = await FileSystem.readAsStringAsync(localUri, {
        encoding: FileSystem.EncodingType.Base64,
        position: offset,
        length,
      });

      const binaryString = atob(chunk);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      await fetch(upload_url, {
        method: "PUT",
        headers: {
          "Content-Type": "audio/mp4",
          "Content-Range": `bytes ${offset}-${offset + length - 1}/${totalSize}`,
        },
        body: bytes.buffer,
      });

      offset += length;
    }
  }

  return recording_id;
}

export async function uploadWithOfflineQueue(
  localUri: string,
  studioId: string,
  assignmentId: string,
  durationSeconds: number,
): Promise<string | null> {
  try {
    const recordingId = await uploadRecording(
      localUri,
      studioId,
      assignmentId,
      durationSeconds,
    );
    return recordingId;
  } catch {
    // Upload failed — queue for later
    useSessionStore.getState().addPendingRecording({
      localUri,
      studioId,
      assignmentId,
      durationSeconds,
      createdAt: new Date().toISOString(),
    });
    return null;
  }
}
