// Model and lab reference facts for the hover cards. Every value is sourced;
// anything unconfirmed is left undefined rather than guessed. Researched
// 2026-11-01 from vendor model pages and publisher model cards, plus
// `ollama show` on the lab server for quantization and serving.
//
// Logos: @lobehub/icons-static-svg (MIT). The marks remain the labs'
// trademarks, used here only to identify each model's developer.
import metaColor from "@lobehub/icons-static-svg/icons/meta-color.svg?raw";
import nvidia from "@lobehub/icons-static-svg/icons/nvidia.svg?raw";
import openai from "@lobehub/icons-static-svg/icons/openai.svg?raw";
import qwenColor from "@lobehub/icons-static-svg/icons/qwen-color.svg?raw";
import zai from "@lobehub/icons-static-svg/icons/zai.svg?raw";

export interface Lab {
  id: string;
  name: string;
  /** Brand color as CSS; theme-adaptive where the brand is black or white. */
  color?: string;
  /** Inline SVG markup. Monochrome marks use currentColor. */
  svg?: string;
}

export interface ModelInfo {
  lab?: string;
  family?: string;
  tier?: string;
  weights?: "Open weights" | "API only";
  size?: string;
  license?: string;
  released?: string;
  summary?: string;
  served?: string;
  sources: { label: string; url?: string }[];
}

export const LABS: Record<string, Lab> = {
  openai: { id: "openai", name: "OpenAI", color: "var(--fg)", svg: openai },
  zai: { id: "zai", name: "Z.ai", color: "var(--fg)", svg: zai },
  qwen: { id: "qwen", name: "Qwen (Alibaba)", svg: qwenColor },
  meta: { id: "meta", name: "Meta", svg: metaColor },
  // #76B900 is the green in NVIDIA's trademark and logo usage guidelines.
  nvidia: { id: "nvidia", name: "NVIDIA", color: "#76B900", svg: nvidia },
};

const OLLAMA_LAB = "Ollama on the lab server";

export const MODELS: Record<string, ModelInfo> = {
  "gpt-6-luna": {
    lab: "openai",
    family: "GPT-6",
    tier: "Luna · fastest tier",
    weights: "API only",
    released: "Sep 2026",
    summary: "OpenAI's most efficient GPT-6 model, for focused, high-volume tasks.",
    served: "OpenAI API",
    sources: [{ label: "OpenAI model page", url: "https://developers.openai.com/api/docs/models/gpt-6-luna" }],
  },
  "gpt-5.6-luna": {
    lab: "openai",
    family: "GPT-5.6",
    tier: "Luna · nano-class tier",
    weights: "API only",
    released: "Jul 2026",
    summary: "GPT-5.6 model optimized for cost-sensitive workloads.",
    served: "OpenAI API",
    sources: [{ label: "OpenAI model page", url: "https://developers.openai.com/api/docs/models/gpt-5.6-luna" }],
  },
  "gpt-5-mini": {
    lab: "openai",
    family: "GPT-5",
    tier: "Mini · deprecated",
    weights: "API only",
    released: "Aug 2025",
    summary: "Strong intelligence for cost-sensitive, low-latency, high-volume workloads.",
    served: "OpenAI API",
    sources: [{ label: "OpenAI model page", url: "https://developers.openai.com/api/docs/models/gpt-5-mini" }],
  },
  "gpt-5-nano": {
    lab: "openai",
    family: "GPT-5",
    tier: "Nano · deprecated",
    weights: "API only",
    released: "Aug 2025",
    summary: "The fastest, most cost-efficient version of GPT-5.",
    served: "OpenAI API",
    sources: [{ label: "OpenAI model page", url: "https://developers.openai.com/api/docs/models/gpt-5-nano" }],
  },
  "glm-4.7-flash": {
    lab: "zai",
    family: "GLM-4.7",
    tier: "Flash · lightweight",
    weights: "Open weights",
    size: "30B MoE, 3B active",
    license: "MIT",
    released: "Jan 2026",
    summary: "Z.ai's 30B-class model built for lightweight deployment.",
    served: `${OLLAMA_LAB} · Q4_K_M`,
    sources: [
      { label: "Hugging Face card", url: "https://huggingface.co/zai-org/GLM-4.7-Flash" },
      { label: "ollama show (lab)" },
    ],
  },
  "qwen3.8:27b": {
    lab: "qwen",
    family: "Qwen3.8",
    tier: "27B dense",
    weights: "Open weights",
    size: "27B dense, vision-language",
    license: "Apache 2.0",
    released: "Aug 2026",
    summary: "Compact, deployment-friendly dense model with native vision-language support.",
    served: "Ollama, local · no longer installed on the lab",
    sources: [{ label: "Hugging Face card", url: "https://huggingface.co/Qwen/Qwen3.8-27B" }],
  },
  "oss-20b": {
    lab: "openai",
    family: "gpt-oss",
    tier: "20B · smaller size",
    weights: "Open weights",
    size: "21B MoE, 3.6B active",
    license: "Apache 2.0",
    released: "Aug 2025",
    summary: "OpenAI's open-weight model for lower-latency, local, or specialized use. Local alias of gpt-oss:20b.",
    served: `${OLLAMA_LAB} · MXFP4`,
    sources: [
      { label: "Hugging Face card", url: "https://huggingface.co/openai/gpt-oss-20b" },
      { label: "ollama show (lab)" },
    ],
  },
  "muse-glimmer:30b": {
    lab: "meta",
    family: "Muse",
    tier: "Open 30B · distilled from Muse Spark",
    weights: "Open weights",
    size: "~30B dense, includes a ~2B vision encoder",
    license: "Apache 2.0",
    released: "Aug 2026",
    summary: "Meta Superintelligence Labs' open model built for always-on local agents.",
    served: `${OLLAMA_LAB} · Q4_K_M`,
    sources: [
      { label: "Hugging Face card", url: "https://huggingface.co/meta-models/Muse-Glimmer-30B" },
      { label: "Ollama", url: "https://ollama.com/library/muse-glimmer" },
    ],
  },
  "nemotron-cascade-2:30b": {
    lab: "nvidia",
    family: "Nemotron",
    tier: "Cascade 2 · 30B-A3B",
    weights: "Open weights",
    size: "30B hybrid Mamba-Transformer MoE, 3B active",
    license: "NVIDIA Open Model License",
    released: "Mar 2026",
    summary: "Open 30B MoE model with 3B active parameters for reasoning and agentic work.",
    served: `${OLLAMA_LAB} · Q4_K_M`,
    sources: [
      { label: "Hugging Face card", url: "https://huggingface.co/nvidia/Nemotron-Cascade-2-30B-A3B" },
      { label: "ollama show (lab)" },
    ],
  },
};

const normalize = (id: string) => id.replace(/:latest$/, "");

export function modelInfo(id: string): ModelInfo | undefined {
  return MODELS[normalize(id)];
}

export function labOf(id: string): Lab | undefined {
  const lab = modelInfo(id)?.lab;
  return lab ? LABS[lab] : undefined;
}
