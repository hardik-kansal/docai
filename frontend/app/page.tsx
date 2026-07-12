"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

export default function RootPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      // Always land on /query after login
      if (user) {
        router.replace("/query");
      } else {
        router.replace("/login");
      }
    }
  }, [user, loading, router]);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg-base)",
      }}
    >
      <div className="spinner spinner-lg" />
    </div>
  );
}
