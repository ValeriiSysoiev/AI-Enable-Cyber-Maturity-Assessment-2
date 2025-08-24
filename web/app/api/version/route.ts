export const runtime = "edge";
export async function GET(){
  const sha = process.env.NEXT_PUBLIC_BUILD_SHA || "unknown";
  return new Response(JSON.stringify({ sha }), { status:200, headers:{ "content-type":"application/json" }});
}
