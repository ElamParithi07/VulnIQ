import dotenv from "dotenv";

dotenv.config();

function required(name: string): string {
  const value = process.env[name];

  if (!value) {
    throw new Error(`Missing environment variable: ${name}`);
  }

  return value;
}

export const env = {
  SUPABASE_URL: required("SUPABASE_URL"),

  SUPABASE_SERVICE_ROLE_KEY: required(
    "SUPABASE_SERVICE_ROLE_KEY"
  ),

  NVD_API_KEY: process.env.NVD_API_KEY ?? "",
};