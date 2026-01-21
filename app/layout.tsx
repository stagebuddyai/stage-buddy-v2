import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stage Buddy",
  description: "Stage Buddy AI Application",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
