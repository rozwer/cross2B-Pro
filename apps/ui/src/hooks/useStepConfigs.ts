/**
 * Hook to load step configs with backend-aware cache invalidation.
 *
 * Problem: localStorage "workflow-config" can become stale when the backend
 * default model changes (e.g., GEMINI_DEFAULT_MODEL updated). Because the
 * frontend prioritizes localStorage over backend defaults, stale model names
 * get sent to the API, causing 404 errors.
 *
 * Solution: On mount, fetch the backend's default model from /api/config/models.
 * Compare it against the cached "workflow-config-default-model" in localStorage.
 * If they differ, the cache is stale — clear it and rebuild from backend defaults.
 */

import { useState, useEffect, useCallback } from "react";
import type { StepConfig } from "@/components/workflow/NodeConfigPanel";
import { WORKFLOW_STEPS } from "@/components/workflow";
import { api } from "@/lib/api";

const STORAGE_KEY = "workflow-config";
const DEFAULT_MODEL_KEY = "workflow-config-default-model";

/**
 * Convert backend StepDefaultConfig (snake_case) to frontend StepConfig (camelCase).
 */
function backendToFrontend(step: {
  step_id: string;
  label: string;
  description: string;
  ai_model: string;
  model_name: string;
  temperature: number;
  grounding: boolean;
  retry_limit: number;
  repair_enabled: boolean;
  is_configurable: boolean;
  recommended_model: string;
}): StepConfig {
  return {
    stepId: step.step_id,
    label: step.label,
    description: step.description,
    aiModel: step.ai_model as StepConfig["aiModel"],
    modelName: step.model_name,
    temperature: step.temperature,
    grounding: step.grounding,
    retryLimit: step.retry_limit,
    repairEnabled: step.repair_enabled,
    isConfigurable: step.is_configurable,
    recommendedModel: step.recommended_model as StepConfig["recommendedModel"],
  };
}

interface UseStepConfigsResult {
  stepConfigs: StepConfig[];
  setStepConfigs: React.Dispatch<React.SetStateAction<StepConfig[]>>;
  isLoading: boolean;
  saveConfigs: (configs: StepConfig[]) => void;
  resetConfigs: () => void;
}

export function useStepConfigs(): UseStepConfigsResult {
  const [stepConfigs, setStepConfigs] = useState<StepConfig[]>(WORKFLOW_STEPS);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadConfigs() {
      try {
        // 1. Fetch backend defaults
        const data = await api.config.getModels();
        const backendDefault = data.providers?.[0]?.default_model ?? "";
        const cachedDefault = localStorage.getItem(DEFAULT_MODEL_KEY);

        if (!cancelled) {
          if (cachedDefault && cachedDefault === backendDefault) {
            // Cache is still valid — use localStorage if present
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
              try {
                setStepConfigs(JSON.parse(saved));
              } catch {
                // Corrupt cache — rebuild from backend
                const configs = data.step_defaults.map(backendToFrontend);
                setStepConfigs(configs);
                localStorage.setItem(STORAGE_KEY, JSON.stringify(configs));
                localStorage.setItem(DEFAULT_MODEL_KEY, backendDefault);
              }
            } else {
              // No saved config — use backend defaults
              const configs = data.step_defaults.map(backendToFrontend);
              setStepConfigs(configs);
            }
          } else {
            // Backend default changed or no cached default — rebuild from backend
            console.info(
              `[useStepConfigs] Backend default changed: ${cachedDefault} → ${backendDefault}. Refreshing config.`
            );
            const configs = data.step_defaults.map(backendToFrontend);
            setStepConfigs(configs);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(configs));
            localStorage.setItem(DEFAULT_MODEL_KEY, backendDefault);
          }
        }
      } catch (err) {
        // Backend unreachable — fall back to localStorage or hardcoded
        if (!cancelled) {
          const saved = localStorage.getItem(STORAGE_KEY);
          if (saved) {
            try {
              setStepConfigs(JSON.parse(saved));
            } catch {
              setStepConfigs(WORKFLOW_STEPS);
            }
          }
          console.warn("[useStepConfigs] Failed to fetch backend config, using cached/fallback", err);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadConfigs();
    return () => { cancelled = true; };
  }, []);

  const saveConfigs = useCallback((configs: StepConfig[]) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(configs));
  }, []);

  const resetConfigs = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(DEFAULT_MODEL_KEY);
    // Will be re-fetched from backend on next mount
    setStepConfigs(WORKFLOW_STEPS);
  }, []);

  return { stepConfigs, setStepConfigs, isLoading, saveConfigs, resetConfigs };
}
