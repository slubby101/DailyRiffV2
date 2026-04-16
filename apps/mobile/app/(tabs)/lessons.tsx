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
import { fetchStudentLessons } from "../../src/lib/api";

export default function LessonsScreen() {
  const user = useSessionStore((s) => s.user);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["student-lessons", user?.id],
    queryFn: () => fetchStudentLessons(user!.id),
    enabled: !!user,
  });

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.emptyText}>Please sign in to view lessons.</Text>
      </SafeAreaView>
    );
  }

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator size="large" color="#D97706" accessibilityLabel="Loading lessons" />
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.errorText}>Failed to load lessons.</Text>
        <Pressable onPress={() => refetch()} style={styles.retryButton} accessibilityRole="button">
          <Text style={styles.retryText}>Retry</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  const lessons = data ?? [];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.heading} accessibilityRole="header">
          Lessons
        </Text>

        {lessons.length === 0 ? (
          <Text style={styles.emptyText}>No lessons scheduled.</Text>
        ) : (
          lessons.map((lesson) => (
            <View key={lesson.id} style={styles.card}>
              <View style={styles.cardHeader}>
                <Text style={styles.cardDate}>{lesson.date}</Text>
                <View
                  style={[
                    styles.statusBadge,
                    lesson.attendance_status === "present"
                      ? styles.badgePresent
                      : lesson.attendance_status === "absent"
                        ? styles.badgeAbsent
                        : styles.badgePending,
                  ]}
                >
                  <Text style={styles.statusText}>
                    {lesson.attendance_status ?? "upcoming"}
                  </Text>
                </View>
              </View>
              <Text style={styles.cardTime}>
                {lesson.start_time} - {lesson.end_time}
              </Text>
              {lesson.teacher_notes ? (
                <Text style={styles.notes}>{lesson.teacher_notes}</Text>
              ) : null}
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
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  cardDate: { fontSize: 16, fontWeight: "600", color: "#1C1917" },
  cardTime: { fontSize: 14, color: "#78716C", marginTop: 4 },
  notes: { fontSize: 13, color: "#57534E", marginTop: 8, fontStyle: "italic" },
  statusBadge: { borderRadius: 12, paddingHorizontal: 10, paddingVertical: 2 },
  badgePresent: { backgroundColor: "#D1FAE5" },
  badgeAbsent: { backgroundColor: "#FEE2E2" },
  badgePending: { backgroundColor: "#FEF3C7" },
  statusText: { fontSize: 12, fontWeight: "500", textTransform: "capitalize" },
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
