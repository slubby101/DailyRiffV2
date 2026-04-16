import { useState, useRef } from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import type { RecordingSession } from "../lib/recording";

interface RecordingWidgetProps {
  assignmentId: string;
  studioId: string;
  onDone: () => void;
}

export function RecordingWidget({
  assignmentId,
  studioId,
  onDone,
}: RecordingWidgetProps) {
  const [status, setStatus] = useState<
    "idle" | "recording" | "uploading" | "done" | "error"
  >("idle");
  const [elapsed, setElapsed] = useState(0);
  const sessionRef = useRef<RecordingSession | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleStart = async () => {
    try {
      // Dynamic import to avoid loading expo-av in tests
      const { startRecording } = await import("../lib/recording");
      const session = await startRecording();
      sessionRef.current = session;
      setStatus("recording");
      setElapsed(0);
      timerRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } catch {
      setStatus("error");
    }
  };

  const handleStop = async () => {
    if (!sessionRef.current) return;
    if (timerRef.current) clearInterval(timerRef.current);

    try {
      const { stopRecording, uploadWithOfflineQueue } = await import(
        "../lib/recording"
      );
      setStatus("uploading");
      const { uri, durationSeconds } = await stopRecording(
        sessionRef.current,
      );
      await uploadWithOfflineQueue(uri, studioId, assignmentId, durationSeconds);
      setStatus("done");
      onDone();
    } catch {
      setStatus("error");
    }
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <View style={styles.container} accessibilityLabel="Recording widget">
      {status === "idle" && (
        <Pressable
          style={styles.startButton}
          onPress={handleStart}
          accessibilityRole="button"
          accessibilityLabel="Start recording"
        >
          <Text style={styles.buttonText}>Start Recording</Text>
        </Pressable>
      )}

      {status === "recording" && (
        <View style={styles.recordingArea}>
          <View style={styles.recordingIndicator} />
          <Text style={styles.timer} accessibilityLiveRegion="polite">
            {formatTime(elapsed)}
          </Text>
          <Pressable
            style={styles.stopButton}
            onPress={handleStop}
            accessibilityRole="button"
            accessibilityLabel="Stop recording"
          >
            <Text style={styles.buttonText}>Stop</Text>
          </Pressable>
        </View>
      )}

      {status === "uploading" && (
        <Text style={styles.statusText}>Uploading...</Text>
      )}

      {status === "done" && (
        <Text style={styles.successText}>Recording uploaded!</Text>
      )}

      {status === "error" && (
        <View>
          <Text style={styles.errorText}>Recording failed.</Text>
          <Pressable
            style={styles.retryButton}
            onPress={() => setStatus("idle")}
            accessibilityRole="button"
          >
            <Text style={styles.retryText}>Try Again</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 12, padding: 12, backgroundColor: "#FEF3C7", borderRadius: 8 },
  startButton: {
    backgroundColor: "#DC2626",
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
  },
  stopButton: {
    backgroundColor: "#57534E",
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 24,
  },
  buttonText: { color: "#FFFFFF", fontWeight: "600", fontSize: 14 },
  recordingArea: { flexDirection: "row", alignItems: "center", gap: 12 },
  recordingIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: "#DC2626",
  },
  timer: { fontSize: 20, fontWeight: "700", color: "#1C1917", flex: 1 },
  statusText: { fontSize: 14, color: "#78716C", textAlign: "center" },
  successText: { fontSize: 14, color: "#059669", textAlign: "center", fontWeight: "600" },
  errorText: { fontSize: 14, color: "#DC2626", textAlign: "center" },
  retryButton: { marginTop: 8, alignItems: "center" },
  retryText: { color: "#D97706", fontWeight: "600" },
});
