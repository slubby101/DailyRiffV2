import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  Switch,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useSessionStore } from "../../src/stores/sessionStore";

export default function ProfileScreen() {
  const user = useSessionStore((s) => s.user);
  const clearSession = useSessionStore((s) => s.clearSession);
  const [pushEnabled, setPushEnabled] = useState(true);
  const [emailEnabled, setEmailEnabled] = useState(true);

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.emptyText}>Please sign in to view your profile.</Text>
      </SafeAreaView>
    );
  }

  const handleSignOut = () => {
    Alert.alert("Sign Out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        style: "destructive",
        onPress: () => clearSession(),
      },
    ]);
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      "Delete Account",
      "This action cannot be undone. All your data will be permanently deleted.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: () => {
            // Account deletion request would go here
          },
        },
      ],
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.heading} accessibilityRole="header">
          Profile
        </Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Account</Text>
          <View style={styles.row}>
            <Text style={styles.label}>Email</Text>
            <Text style={styles.value}>{user.email}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>User ID</Text>
            <Text style={styles.valueMono}>{user.id.slice(0, 8)}...</Text>
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Notifications</Text>
          <View style={styles.switchRow}>
            <Text style={styles.label}>Push Notifications</Text>
            <Switch
              value={pushEnabled}
              onValueChange={setPushEnabled}
              trackColor={{ true: "#D97706" }}
              accessibilityLabel="Toggle push notifications"
            />
          </View>
          <View style={styles.switchRow}>
            <Text style={styles.label}>Email Notifications</Text>
            <Switch
              value={emailEnabled}
              onValueChange={setEmailEnabled}
              trackColor={{ true: "#D97706" }}
              accessibilityLabel="Toggle email notifications"
            />
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Security</Text>
          <Pressable style={styles.actionButton} accessibilityRole="button">
            <Text style={styles.actionText}>Change Password</Text>
          </Pressable>
        </View>

        <Pressable
          style={styles.signOutButton}
          onPress={handleSignOut}
          accessibilityRole="button"
        >
          <Text style={styles.signOutText}>Sign Out</Text>
        </Pressable>

        <Pressable
          style={styles.deleteButton}
          onPress={handleDeleteAccount}
          accessibilityRole="button"
        >
          <Text style={styles.deleteText}>Delete Account</Text>
        </Pressable>
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
  cardTitle: { fontSize: 16, fontWeight: "600", color: "#44403C", marginBottom: 12 },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 6,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#E7E5E4",
  },
  switchRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 8,
  },
  label: { fontSize: 14, color: "#57534E" },
  value: { fontSize: 14, color: "#1C1917", fontWeight: "500" },
  valueMono: { fontSize: 14, color: "#1C1917", fontFamily: "monospace" },
  actionButton: {
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#E7E5E4",
  },
  actionText: { fontSize: 14, color: "#D97706", fontWeight: "500" },
  signOutButton: {
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#D6D3D1",
  },
  signOutText: { fontSize: 16, fontWeight: "600", color: "#57534E" },
  deleteButton: {
    paddingVertical: 14,
    alignItems: "center",
  },
  deleteText: { fontSize: 14, color: "#DC2626" },
  emptyText: { fontSize: 14, color: "#A8A29E", textAlign: "center", padding: 16 },
});
