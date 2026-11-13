export type StepStatus = "pending" | "running" | "done" | "failed" | "skipped";
export type ProjectStatus = "uploaded" | "queued" | "processing" | "completed" | "failed";

export interface Step { key: string; label: string; status: StepStatus; progress: number; message: string; error: string }
export interface Frame { id: string; kind: string; timestamp: number; url: string; width: number; height: number; is_representative: boolean; filename: string }
export interface Scene {
  id: string; index: number; start: number; end: number; duration: number; target_duration: number | null;
  selected: boolean; data: Record<string, string>; character_indexes: number[]; description: string;
  prompt_sections: Record<string, string>; prompt_text: string; frames: Frame[];
}
export interface Character { id: string; index: number; label: string; data: Record<string, string>; prompt_descriptor: string; scene_indexes: number[]; reference_url: string | null }
export interface Dialogue {
  id: string; scene_index: number | null; start: number; end: number; text: string; language: string;
  character_index: number | null; tone: string; emotion: string; intensity: string; pace: string;
  identifiable: boolean; edited: boolean;
}
export interface ProjectSummary {
  id: string; name: string; status: ProjectStatus; created_at: string; completed_at: string | null;
  duration: number; width: number; height: number; fps: number; format: string; orientation: string;
  file_size: number; original_filename: string; source_type: string; scene_count: number;
  character_count: number; thumbnail_url: string | null; storage_bytes: number; error: string;
}
export interface Project extends ProjectSummary {
  has_audio: boolean; split_mode: "smart" | "fixed"; split_seconds: number; language: string; mood: string;
  visual_style: string; summary: string; prompt_language: string; prompt_style: string; global_prompt: string;
  source_available: boolean; video_url: string | null; steps: Step[]; scenes: Scene[];
  characters: Character[]; dialogues: Dialogue[];
}
export interface Progress { status: ProjectStatus; error: string; steps: Step[]; scene_count: number; character_count: number }
export interface Meta {
  styles: { key: string; label: string }[]; languages: { code: string; label: string }[];
  split_seconds: number[]; steps: { key: string; label: string }[];
  limits: { max_upload_mb: number; max_duration_seconds: number; extensions: string[] };
  providers: Record<"vision" | "llm" | "transcription", { name: string; configured: boolean }>;
}
export interface Dashboard {
  videos_analyzed: number; in_progress: number; completed: number; failed: number; total_projects: number;
  total_duration_analyzed: number; storage_bytes: number; recent: ProjectSummary[];
}
export interface User { id: string; email: string; name: string }
