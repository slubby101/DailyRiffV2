"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface Conversation {
  id: string;
  studio_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  body: string;
  created_at: string;
}

function useConversations() {
  return useQuery<Conversation[]>({
    queryKey: ["parent", "conversations"],
    queryFn: () => apiFetch("/conversations"),
  });
}

function useMessages(conversationId: string) {
  return useQuery<Message[]>({
    queryKey: ["parent", "conversations", conversationId, "messages"],
    queryFn: () => apiFetch(`/conversations/${conversationId}/messages`),
    enabled: !!conversationId,
    refetchInterval: 10_000,
  });
}

export default function ParentMessagesPage() {
  const queryClient = useQueryClient();
  const conversations = useConversations();
  const [selectedId, setSelectedId] = useState<string>("");
  const [newMessage, setNewMessage] = useState("");

  const messages = useMessages(selectedId);

  const sendMessage = useMutation({
    mutationFn: (body: string) =>
      apiFetch(`/conversations/${selectedId}/messages`, {
        method: "POST",
        body: JSON.stringify({ body }),
      }),
    onSuccess: () => {
      setNewMessage("");
      queryClient.invalidateQueries({
        queryKey: ["parent", "conversations", selectedId, "messages"],
      });
    },
  });

  const markRead = useMutation({
    mutationFn: (conversationId: string) =>
      apiFetch(`/conversations/${conversationId}/read`, { method: "POST" }),
  });

  function handleSelectConversation(id: string) {
    setSelectedId(id);
    markRead.mutate(id);
  }

  if (conversations.isLoading) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-muted-foreground">Loading messages...</p>
      </div>
    );
  }

  if (conversations.error) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-destructive" role="alert">
          Failed to load conversations.
        </p>
      </div>
    );
  }

  const convos = conversations.data!;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-8">
        <h1 className="font-display text-[40px] leading-[48px] font-semibold tracking-tight">
          Messages
        </h1>
        <p className="text-muted-foreground mt-2">
          Communicate with your child&apos;s teacher.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-[300px_1fr]">
        {/* Conversation list */}
        <div>
          {convos.length === 0 ? (
            <p className="text-muted-foreground">No conversations yet.</p>
          ) : (
            <ul className="space-y-2">
              {convos.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => handleSelectConversation(c.id)}
                    className={`w-full rounded-md border p-3 text-left transition-colors ${
                      selectedId === c.id
                        ? "border-primary bg-primary/5"
                        : "hover:bg-muted"
                    }`}
                  >
                    <p className="text-sm font-medium">
                      Conversation
                    </p>
                    <p className="text-muted-foreground text-xs">
                      {new Date(c.updated_at).toLocaleDateString()}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Message thread */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {selectedId ? "Thread" : "Select a conversation"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedId && messages.data ? (
              <>
                <div
                  className="mb-4 max-h-96 space-y-3 overflow-y-auto"
                  role="log"
                  aria-live="polite"
                  aria-label="Message thread"
                >
                  {messages.data.length === 0 ? (
                    <p className="text-muted-foreground text-sm">
                      No messages in this conversation yet.
                    </p>
                  ) : (
                    messages.data.map((m) => (
                      <div key={m.id} className="rounded-md border p-3">
                        <p className="text-sm">{m.body}</p>
                        <p className="text-muted-foreground mt-1 text-xs">
                          {new Date(m.created_at).toLocaleString()}
                        </p>
                      </div>
                    ))
                  )}
                </div>

                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (newMessage.trim()) {
                      sendMessage.mutate(newMessage.trim());
                    }
                  }}
                  className="flex gap-2"
                >
                  <Textarea
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Type a message..."
                    className="min-h-[60px]"
                    aria-label="Message input"
                  />
                  <Button
                    type="submit"
                    disabled={!newMessage.trim() || sendMessage.isPending}
                  >
                    {sendMessage.isPending ? "Sending..." : "Send"}
                  </Button>
                </form>
              </>
            ) : (
              <p className="text-muted-foreground text-sm">
                Select a conversation from the list to view messages.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
