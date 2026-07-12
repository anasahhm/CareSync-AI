/**
 * GestureMed AI — Shared TypeScript Types
 */

export type UserRole = "PATIENT" | "DOCTOR" | "ADMIN";

export type ConsultationStatus =
  | "SCHEDULED"
  | "WAITING"
  | "ACTIVE"
  | "COMPLETED"
  | "CANCELLED";

export type ReportStatus = "PENDING" | "GENERATING" | "COMPLETED" | "FAILED";

export type NotificationLevel = "info" | "success" | "warning" | "critical";

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  avatar_url?: string;
  created_at: string;
}

export interface DoctorProfile {
  specialization: string;
  hospital?: string;
  license_number?: string;
  years_of_experience: number;
  bio?: string;
  consultation_fee?: number;
  is_verified: boolean;
  available: boolean;
}

export interface PatientProfile {
  date_of_birth?: string;
  gender?: string;
  blood_type?: string;
  allergies: string[];
  current_medications: string[];
  medical_history: Record<string, unknown>;
  emergency_contact?: {
    name: string;
    phone: string;
    relationship: string;
  };
}

export interface UserWithProfile extends AuthUser {
  profile?: DoctorProfile | PatientProfile;
}

// ── Consultations ─────────────────────────────────────────────────────────────

export interface Consultation {
  id: string;
  room_id: string;
  status: ConsultationStatus;
  chief_complaint?: string;
  doctor_notes?: string;
  started_at?: string;
  ended_at?: string;
  duration_seconds?: number;
  created_at: string;
}

// ── Annotations ───────────────────────────────────────────────────────────────

export interface AnnotationCoordinates {
  x: number;
  y: number;
  radius?: number;
  width?: number;
  height?: number;
  [key: string]: number | undefined;
}

export interface Annotation {
  id: string;
  type: "point" | "circle" | "region" | "text" | "drawing";
  coordinates: AnnotationCoordinates;
  body_region?: string;
  note?: string;
  color: string;
  created_by?: string;
  role?: UserRole;
  timestamp?: string;
}

// ── Gestures ──────────────────────────────────────────────────────────────────

export type GestureName =
  | "PINCH"
  | "PEACE"
  | "POINTING"
  | "THUMBS_UP"
  | "THUMBS_DOWN"
  | "OPEN_PALM"
  | "FIST"
  | "FINGERS_1"
  | "FINGERS_2"
  | "FINGERS_3"
  | "FINGERS_4"
  | "FINGERS_5"
  | "NONE";

export interface GestureResult {
  gesture: GestureName;
  confidence: number;
  hands_detected: number;
  metadata: Record<string, unknown>;
  landmarks?: Array<Array<{ x: number; y: number; z: number }>>;
  action?: GestureAction;
}

export interface GestureAction {
  type: string;
  message: string;
  level: NotificationLevel;
  metadata: Record<string, unknown>;
}

// ── AI Reports ────────────────────────────────────────────────────────────────

export interface AIReport {
  id: string;
  consultation_id: string;
  status: ReportStatus;
  summary?: string;
  symptoms_observed?: string[];
  areas_marked?: string[];
  suggested_next_steps?: string[];
  risk_indicators?: string[];
  structured_data?: {
    doctor_assessment_notes?: string;
    patient_complaints?: string[];
    follow_up_recommendation?: string;
    ai_disclaimer: string;
  };
  generated_at?: string;
  created_at: string;
}

// ── Doctors (public) ──────────────────────────────────────────────────────────

export interface DoctorListing {
  id: string;
  full_name: string;
  specialization: string;
  hospital?: string;
  years_of_experience: number;
  bio?: string;
  consultation_fee?: number;
  is_verified: boolean;
  available: boolean;
}

// ── Notifications (in-app) ────────────────────────────────────────────────────

export interface AppNotification {
  id: string;
  message: string;
  level: NotificationLevel;
  timestamp?: string;
}
