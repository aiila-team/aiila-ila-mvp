import { useEffect, useState } from 'react';
import client from '../api/client';
import { Entity, PaginatedResponse } from '../types';
import { useEntityStore } from '../store';

interface UseEntitiesOptions {
  page?: number;
  page_size?: number;
  type?: string;
  search?: string;
}

export const useEntities = (options: UseEntitiesOptions = {}) => {
  const { setEntities, setLoading } = useEntityStore();
  const entities = useEntityStore((s) => s.entities);
  const isLoading = useEntityStore((s) => s.isLoading);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      setError(null);
      try {
        const { data } = await client.get<PaginatedResponse<Entity>>('/entities', {
          params: options,
        });
        setEntities(data.items);
        setTotal(data.total);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to fetch entities');
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [options.page, options.page_size, options.type, options.search]);

  return { entities, isLoading, error, total };
};
