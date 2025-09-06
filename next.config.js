/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Configure the app directory location  
  pageExtensions: ['ts', 'tsx', 'js', 'jsx'],
  outputFileTracingRoot: __dirname,
}

module.exports = nextConfig