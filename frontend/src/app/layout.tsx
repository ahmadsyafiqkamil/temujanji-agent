import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Temujanji KJRI",
  description: "Appointment and check-in portal",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
