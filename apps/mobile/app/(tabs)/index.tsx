import { useEffect } from "react";
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
import { fetchStudentDashboard } from "../../src/lib/api";

export default function DashboardScreen() {
  const user = useSessionStore((s) => s.user);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["student-dashboard", user?.id],
    queryFn: () => fetchStudentDashboard(user!.id),
    enabled: !!user,
  });

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.emptyText}>Please sign in to view your dashboard.</Text>
      </SafeAreaView>
    );
  }

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator size="large" color="#D97706" accessibilityLabel="Loading dashboard" />
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.errorText}>Failed to load dashboard.</Text>
        <Pressable onPress={() => refetch()} style={styles.retryButton} accessibilityRole="button">
          <Text style={styles.retryText}>Retry</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  const streak = data?.streak;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.heading} accessibilityRole="header">
          Dashboard
        </Text>

        <View style={styles.card} accessibilityLabel="Practice streak">
          <Text style={styles.cardTitle}>Practice Streak</Text>
          <Text style={styles.streakNumber}>{streak?.current_streak ?? 0}</Text>
          <Text style={styles.streakLabel}>
            {streak?.is_active ? "days active" : "days (inactive)"}
          </Text>
          <Text style={styles.meta}>
            Longest: {streak?.longest_streak ?? 0} days | Total:{" "}
            {streak?.total_practice_days ?? 0} days
          </Text>
          <Text style={styles.meta}>
            This week: {streak?.weekly_minutes ?? 0} min
          </Text>
        </View>

        <View style={styles.card} accessibilityLabel="Upcoming assignments">
          <Text style={styles.cardTitle}>Upcoming Assignments</Text>
          {data?.upcoming_assignments?.length ? (
            data.upcoming_assignments.map((a) => (
              <View key={a.id} style={styles.listItem}>
                <Text style={styles.listTitle}>{a.title}</Text>
                <Text style={styles.listMeta}>Due: {a.due_date}</Text>
              </View>
            ))
          ) : (
            <Text style={styles.emptyText}>No upcoming assignments.</Text>
          )}
        </View>

        <View style={styles.card} accessibilityLabel="Recent recordings">
          <Text style={styles.cardTitle}>Recent Recordings</Text>
          {data?.recent_recordings?.length ? (
            data.recent_recordings.map((r) => (
              <View key={r.id} style={styles.listItem}>
                <Text style={styles.listTitle}>
                  {r.duration_seconds
                    ? `${Math.round(r.duration_seconds / 60)} min`
                    : "Recording"}
                </Text>
                <Text style={styles.listMeta}>{r.created_at}</Text>
              </View>
            ))
          ) : (
            <Text style={styles.emptyText}>No recordings yet.</Text>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#FAFAF9" },
  scrollContent: { padding: 16, gap: 16 },
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
  cardTitle: { fontSize: 16, fontWeight: "600", color: "#44403C", marginBottom: 8 },
  streakNumber: { fontSize: 48, fontWeight: "700", color: "#D97706", textAlign: "center" },
  streakLabel: { fontSize: 14, color: "#78716C", textAlign: "center", marginBottom: 8 },
  meta: { fontSize: 12, color: "#A8A29E", textAlign: "center" },
  listItem: {
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#E7E5E4",
  },
  listTitle: { fontSize: 14, fontWeight: "500", color: "#1C1917" },
  listMeta: { fontSize: 12, color: "#78716C", marginTop: 2 },
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
