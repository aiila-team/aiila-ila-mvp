import { useEffect, useState } from 'react';
import client from '../api/client';
import { GraphData } from '../types';

export const useGraph = (entityId?: string) => {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!entityId) return;
    const fetch = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data } = await client.get<GraphData>(`/graph/${entityId}`);
        setGraph(data);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to fetch graph');
      } finally {
        setIsLoading(false);
      }
    };
    fetch();
  }, [entityId]);

  return { graph, isLoading, error };
};
