/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // "standalone" : serveur Node autonome, utilisé par l'image Docker tout-en-un.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
};
export default nextConfig;
