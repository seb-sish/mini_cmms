import { handleApiProxy } from "@shared/api/bff";
import { NextResponse } from "next/server";
import { NextRequest } from "next/server";

interface IProxyRouteContext {
  params: Promise<{ path: string[] }>;
}

const proxyRequest = async (
  request: NextRequest,
  { params }: IProxyRouteContext
): Promise<NextResponse> => handleApiProxy(request, (await params).path);

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PATCH = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
