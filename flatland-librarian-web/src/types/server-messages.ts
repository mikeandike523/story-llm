
export interface TaskBeginResponse {
  task_id: string;
}

export interface TaskRequest {
  task_id: string;
  payload: string; // Adjust if the payload structure changes
}

export interface ProgressUpdate {
  progress: number;
  message: string;
}

export interface TaskMessage {
  message: string;
}

export interface TaskDone {
  result: string;
}

export interface TaskError {
  message: string;
}