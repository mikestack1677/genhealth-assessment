import axios from "axios";
import type { ApiError } from "./types";

const client = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

client.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response) {
      const data = error.response.data as ApiError;
      const message = data?.detail ?? "An unexpected error occurred";
      return Promise.reject(new Error(message));
    }
    return Promise.reject(error);
  },
);

export default client;
