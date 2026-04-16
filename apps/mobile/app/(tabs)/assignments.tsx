import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Pressable,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useQuery } from "@tanstack/react-query";
import { useSessionStore } from "../../src/stores/sessionStore";
import { fetchStudentAssignments } from "../../src/lib/api";
import { RecordingWidget } from "../../src/components/RecordingWidget";

export default function AssignmentsScreen() {
  const user = useSessionStore((s) => s.user);
  const [recordingForAssignment, setRecordingForAssignment] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["student-assignments", user?.id],
    queryFn: () => fetchStudentAssignments(user!.id),
    enabled: !!user,
  });

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.emptyText}>Please sign in to view assignments.</Text>
      </SafeAreaView>
    );
  }

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator size="large" color="#D97706" accessibilityLabel="Loading assignments" />
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.errorText}>Failed to load assignments.</Text>
        <Pressable onPress={() => refetch()} style={styles.retryButton} accessibilityRole="button">
          <Text style={styles.retryText}>Retry</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  const assignments = data ?? [];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.heading} accessibilityRole="header">
          Assignments
        </Text>

        {assignments.length === 0 ? (
          <Text style={styles.emptyText}>No assignments yet.</Text>
        ) : (
          assignments.map((assignment) => (
            <View key={assignment.id} style={styles.card}>
              <Text style={styles.cardTitle}>{assignment.title}</Text>
              {assignment.description ? (
                <Text style={styles.cardDescription}>{assignment.description}</Text>
              ) : null}
              <View style={styles.cardMeta}>
                <Text style={styles.metaText}>Due: {assignment.due_date}</Text>
                <Text style={styles.metaText}>
                  Pieces: {assignment.pieces?.length ?? 0}
                </Text>
              </View>

              {assignment.pieces?.map((piece, i) => (
                <Text key={i} style={styles.pieceText}>
                  {piece}
                </Text>
              ))}

              <Pressable
                style={styles.recordButton}
                onPress={() => setRecordingForAssignment(assignment.id)}
                accessibilityRole="button"
                accessibilityLabel={`Record practice for ${assignment.title}`}
              >
                <Text style={styles.recordButtonText}>Record Practice</Text>
              </Pressable>

              {recordingForAssignment === assignment.id && (
                <RecordingWidget
                  assignmentId={assignment.id}
                  studioId={assignment.studio_id}
                  onDone={() => {
                    setRecordingForAssignment(null);
                    refetch();
                  }}
                />
              )}
            </View>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#FAFAF9" },
  scrollContent: { padding: 16, gap: 12 },
  heading: { fontSize: 28, fontWeight: "700", color: "#1C1917", marginBottom: 8 },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    padding: 16,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  cardTitle: { fontSize: 16, fontWeight: "600", color: "#1C1917" },
  cardDescription: { fontSize: 14, color: "#57534E", marginTop: 4 },
  cardMeta: { flexDirection: "row", justifyContent: "space-between", marginTop: 8 },
  metaText: { fontSize: 12, color: "#78716C" },
  pieceText: { fontSize: 13, color: "#44403C", marginTop: 4, paddingLeft: 8 },
  recordButton: {
    marginTop: 12,
    backgroundColor: "#D97706",
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
  },
  recordButtonText: { color: "#FFFFFF", fontWeight: "600", fontSize: 14 },
  emptyText: { fontSize: 14, color: "#A8A29E", textAlign: "center", padding: 16 },
  errorText: { fontSize: 16, color: "#DC2626", textAlign: "center", padding: 16 },
  retryButton: {
    alignSelf: "center",
    backgroundColor: "#D97706",
    borderRadius: 8,
    paddingHorizontal: 24,
    paddingVertical: 10,
  },
  retryText: { color: "#FFFFFF", fontWeight: "600" },
});
