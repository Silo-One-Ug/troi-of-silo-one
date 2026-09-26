import type { NextConfig } from "next";
// NEXT_DIST_DIR lets a preview build (next dev on another port) keep its output away from the .next the running console serves
const config: NextConfig = { reactStrictMode: true, transpilePackages: ["three", "mdast-util-gfm-autolink-literal"], distDir: process.env.NEXT_DIST_DIR || ".next" };
export default config;
