import { NextRouter } from "next/router";

export function getEmail(): string {
  if (typeof window !== "undefined") {
    return localStorage.getItem("email") || "";
  }
  return "";
}

export function getEngagementId(): string {
  if (typeof window !== "undefined") {
    return localStorage.getItem("engagementId") || "";
  }
  return "";
}

export function setEngagementId(id: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("engagementId", id);
  }
}

export async function requireEmail(router: any): Promise<string> {
  const email = getEmail();
  if (!email) {
    await router.push("/signin");
    return "";
  }
  return email;
}

export function isAdmin(): boolean {
  const email = getEmail();
  const adminEmails = process.env.NEXT_PUBLIC_ADMIN_EMAILS || "";
  const admins = adminEmails.split(",").map(e => e.trim().toLowerCase());
  return admins.includes(email.toLowerCase());
}
