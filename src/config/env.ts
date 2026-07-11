import dotenv from "dotenv";

dotenv.config();

export const env = {
  SUPABASE_URL: process.env.SUPABASE_URL!,
  SUPABASE_SERVICE_ROLE_KEY:
    process.env.SUPABASE_SERVICE_ROLE_KEY!,

  NVD_API_KEY: process.env.NVD_API_KEY ?? "",
};