import type {
  StudentDashboardResponse,
  AssignmentResponse,
  LessonResponse,
  ConversationResponse,
  RecordingResponse,
} from "@dailyriff/api-client";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchStudentDashboard(
  userId: string,
): Promise<StudentDashboardResponse> {
  return apiFetch<StudentDashboardResponse>(
    `/students/${userId}/dashboard`,
  );
}

export interface StudentLesson {
  id: string;
  date: string;
  start_time: string;
  end_time: string;
  attendance_status: string | null;
  teacher_notes: string | null;
}

export async function fetchStudentLessons(
  userId: string,
): Promise<StudentLesson[]> {
  return apiFetch<StudentLesson[]>(`/students/${userId}/lessons`);
}

export interface StudentAssignment {
  id: string;
  studio_id: string;
  title: string;
  description: string | null;
  due_date: string;
  pieces: string[];
}

export async function fetchStudentAssignments(
  userId: string,
): Promise<StudentAssignment[]> {
  return apiFetch<StudentAssignment[]>(
    `/assignments?student_id=${encodeURIComponent(userId)}`,
  );
}

export interface ConversationSummary {
  id: string;
  participant_names: string[];
  last_message_preview: string | null;
  unread_count: number;
}

export async function fetchConversations(
  userId: string,
): Promise<ConversationSummary[]> {
  return apiFetch<ConversationSummary[]>(`/conversations`);
}

export async function sendMessage(
  conversationId: string,
  body: string,
): Promise<void> {
  await apiFetch(`/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export interface PresignedUploadUrl {
  upload_url: string;
  recording_id: string;
}

export async function requestUploadUrl(
  studioId: string,
  assignmentId: string,
  durationSeconds: number,
): Promise<PresignedUploadUrl> {
  return apiFetch<PresignedUploadUrl>(`/recordings/upload-url`, {
    method: "POST",
    body: JSON.stringify({
      studio_id: studioId,
      assignment_id: assignmentId,
      duration_seconds: durationSeconds,
    }),
  });
}

export async function uploadChunk(
  uploadUrl: string,
  chunk: Blob | ArrayBuffer,
  offset: number,
  totalSize: number,
): Promise<void> {
  await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "Content-Type": "audio/mp4",
      "Content-Range": `bytes ${offset}-${offset + (chunk instanceof Blob ? chunk.size : chunk.byteLength) - 1}/${totalSize}`,
    },
    body: chunk,
  });
}
