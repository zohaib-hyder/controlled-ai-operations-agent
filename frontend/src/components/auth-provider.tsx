"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  useRef,
} from "react";
import type { CurrentUser } from "@/types/auth";
import { api, ApiError } from "@/lib/api";
interface AuthContextValue {
  user: CurrentUser | null;
  loading: boolean;
  error: string;
  expired: boolean;
  refresh: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}
const AuthContext = createContext<AuthContextValue | null>(null);
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const generation = useRef(0);
  const authPending = useRef(false);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expired, setExpired] = useState(false);
  const refresh = useCallback((): Promise<void> => {
    if (authPending.current) return Promise.resolve();
    const version = ++generation.current;
    return api<CurrentUser>("/auth/me", {}, false)
      .then((identity) => {
        if (version !== generation.current) return;
        setUser(identity);
        setError("");
      })
      .catch((error) => {
        if (version !== generation.current) return;
        setUser(null);
        setError(
          error instanceof ApiError && error.status === 401
            ? ""
            : "Unable to check your session. Please try again.",
        );
      })
      .finally(() => {
        if (version === generation.current) setLoading(false);
      });
  }, []);
  useEffect(() => {
    void refresh();
    const expired = () => {
      generation.current++;
      setUser(null);
      setExpired(true);
    };
    window.addEventListener("session-expired", expired);
    const focus = () => {
      void refresh();
    };
    window.addEventListener("focus", focus);
    return () => {
      window.removeEventListener("session-expired", expired);
      window.removeEventListener("focus", focus);
    };
  }, [refresh]);
  async function login(email: string, password: string) {
    authPending.current = true;
    generation.current++;
    try {
      const identity = await api<CurrentUser>(
        "/auth/login",
        { method: "POST", body: JSON.stringify({ email, password }) },
        false,
      );
      setUser(identity);
      setExpired(false);
      setError("");
    } finally {
      authPending.current = false;
    }
  }
  async function logout() {
    authPending.current = true;
    generation.current++;
    try {
      try {
        await api<void>("/auth/logout", { method: "POST" });
      } catch (error) {
        if (!(error instanceof ApiError && error.status === 401)) throw error;
      }
      setUser(null);
      setExpired(false);
    } finally {
      authPending.current = false;
    }
  }
  return (
    <AuthContext
      value={{ user, loading, error, expired, refresh, login, logout }}
    >
      {children}
    </AuthContext>
  );
}
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("AuthProvider is required");
  return context;
}
