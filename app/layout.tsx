import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stage Buddy - Performance Feedback (Beta)",
  description: "Structured performance feedback based on observable delivery signals.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
