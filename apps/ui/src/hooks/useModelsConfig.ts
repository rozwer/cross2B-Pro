/**
 * Hook to fetch models configuration from backend
 *
 * The backend is the source of truth for model names and step defaults.
 * Frontend should always use this hook to get available models.
 */

import { useState, useEffect } from "react";
import type { ModelsConfigResponse, StepDefaultConfig, ProviderConfig } from "@/lib/types";
import { api } from "@/lib/api";

interface UseModelsConfigResult {
  config: ModelsConfigResponse | null;
  stepDefaults: StepDefaultConfig[];
  providers: ProviderConfig[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useModelsConfig(): UseModelsConfigResult {
  const [config, setConfig] = useState<ModelsConfigResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchConfig = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await api.config.getModels();
      setConfig(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to fetch models config"));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  return {
    config,
    stepDefaults: config?.step_defaults ?? [],
    providers: config?.providers ?? [],
    isLoading,
    error,
    refetch: fetchConfig,
  };
}
