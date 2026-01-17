import { NextRequest, NextResponse } from "next/server";

function getApiUrl(): string {
  // Read at runtime, not at module load time
  return process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const helpKey = path.join("/");
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/api/help/${helpKey}`, {
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "Help content not found" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error(`Failed to fetch help content from ${apiUrl}:`, error);
    return NextResponse.json(
      { error: "Failed to fetch help content" },
      { status: 500 }
    );
  }
}
