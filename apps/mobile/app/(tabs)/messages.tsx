import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Pressable,
  TextInput,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSessionStore } from "../../src/stores/sessionStore";
import { fetchConversations, sendMessage } from "../../src/lib/api";

export default function MessagesScreen() {
  const user = useSessionStore((s) => s.user);
  const queryClient = useQueryClient();
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [messageBody, setMessageBody] = useState("");

  const { data: conversations, isLoading, error, refetch } = useQuery({
    queryKey: ["conversations", user?.id],
    queryFn: () => fetchConversations(user!.id),
    enabled: !!user,
  });

  const sendMutation = useMutation({
    mutationFn: (params: { conversationId: string; body: string }) =>
      sendMessage(params.conversationId, params.body),
    onSuccess: () => {
      setMessageBody("");
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.emptyText}>Please sign in to view messages.</Text>
      </SafeAreaView>
    );
  }

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator size="large" color="#D97706" accessibilityLabel="Loading messages" />
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.errorText}>Failed to load messages.</Text>
        <Pressable onPress={() => refetch()} style={styles.retryButton} accessibilityRole="button">
          <Text style={styles.retryText}>Retry</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  const conversationList = conversations ?? [];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.heading} accessibilityRole="header">
          Messages
        </Text>

        {conversationList.length === 0 ? (
          <Text style={styles.emptyText}>No conversations yet.</Text>
        ) : (
          conversationList.map((conversation) => (
            <Pressable
              key={conversation.id}
              style={[
                styles.card,
                selectedConversation === conversation.id && styles.cardSelected,
              ]}
              onPress={() =>
                setSelectedConversation(
                  selectedConversation === conversation.id ? null : conversation.id,
                )
              }
              accessibilityRole="button"
              accessibilityLabel={`Conversation with participants`}
            >
              <View style={styles.cardHeader}>
                <Text style={styles.cardTitle}>
                  {conversation.participant_names?.join(", ") ?? "Conversation"}
                </Text>
                {conversation.unread_count ? (
                  <View style={styles.unreadBadge}>
                    <Text style={styles.unreadText}>{conversation.unread_count}</Text>
                  </View>
                ) : null}
              </View>
              {conversation.last_message_preview ? (
                <Text style={styles.preview} numberOfLines={2}>
                  {conversation.last_message_preview}
                </Text>
              ) : null}

              {selectedConversation === conversation.id && (
                <View style={styles.composeArea}>
                  <TextInput
                    style={styles.input}
                    placeholder="Type a message..."
                    value={messageBody}
                    onChangeText={setMessageBody}
                    multiline
                    accessibilityLabel="Message input"
                  />
                  <Pressable
                    style={[
                      styles.sendButton,
                      (!messageBody.trim() || sendMutation.isPending) &&
                        styles.sendButtonDisabled,
                    ]}
                    onPress={() => {
                      if (messageBody.trim()) {
                        sendMutation.mutate({
                          conversationId: conversation.id,
                          body: messageBody.trim(),
                        });
                      }
                    }}
                    disabled={!messageBody.trim() || sendMutation.isPending}
                    accessibilityRole="button"
                    accessibilityLabel="Send message"
                  >
                    <Text style={styles.sendText}>
                      {sendMutation.isPending ? "Sending..." : "Send"}
                    </Text>
                  </Pressable>
                </View>
              )}
            </Pressable>
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
  cardSelected: { borderColor: "#D97706", borderWidth: 1 },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  cardTitle: { fontSize: 15, fontWeight: "600", color: "#1C1917", flex: 1 },
  preview: { fontSize: 13, color: "#78716C", marginTop: 4 },
  unreadBadge: {
    backgroundColor: "#D97706",
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 6,
  },
  unreadText: { color: "#FFFFFF", fontSize: 11, fontWeight: "700" },
  composeArea: { marginTop: 12, gap: 8 },
  input: {
    borderWidth: 1,
    borderColor: "#D6D3D1",
    borderRadius: 8,
    padding: 10,
    fontSize: 14,
    minHeight: 60,
    textAlignVertical: "top",
  },
  sendButton: {
    backgroundColor: "#D97706",
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
  },
  sendButtonDisabled: { opacity: 0.5 },
  sendText: { color: "#FFFFFF", fontWeight: "600" },
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
