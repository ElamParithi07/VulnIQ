import supabase from "../../config/supabase";
import { Intelligence } from "../../types/intelligence";

export async function findCachedAnalysis(id: string) {
  const { data, error } = await supabase
    .from("vulnerability_cache")
    .select(`
      title,
      ai_summary,
      business_impact,
      priority_reason,
      ai_playbook
    `)
    .eq("id", id)
    .maybeSingle();

  if (error) {
    throw error;
  }

  if (!data?.ai_summary) {
    return null;
  }

  return {
    title: data.title,
    summary: data.ai_summary,
    businessImpact: data.business_impact,
    priorityReason: data.priority_reason,
    remediation: data.ai_playbook,
  } satisfies Intelligence;
}

export async function saveAnalysis(
  id: string,
  intelligence: Intelligence
) {
  const { error } = await supabase
    .from("vulnerability_cache")
    .update({
      title: intelligence.title,
      ai_summary: intelligence.summary,
      business_impact: intelligence.businessImpact,
      priority_reason: intelligence.priorityReason,
      ai_playbook: intelligence.remediation,
    })
    .eq("id", id);

  if (error) {
    throw error;
  }
}