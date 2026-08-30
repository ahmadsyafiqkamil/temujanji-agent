import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KJRI Appointments",
  description: "Appointment and check-in portal",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // Extensions (e.g. Scribe) inject attributes onto <html>/<body> before hydrate.
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
