import { useQuery, useQueryClient } from "@tanstack/react-query";
import { integrationsApi } from "../integrationsApi";
import { IntegrationCard } from "../components/IntegrationCard";
import { LibraryHealthSkeleton } from "@/components/common/ResearchSkeletons";

export function IntegrationsSection() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["integrations-catalog"],
    queryFn: integrationsApi.catalog,
    staleTime: 15_000,
  });

  if (isLoading) return <LibraryHealthSkeleton />;
  if (error || !data) {
    return (
      <p className="text-sm text-muted-foreground">
        Could not load integrations catalog.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <p className="text-sm text-muted-foreground">
        Single source of truth for every connector. Live vs Coming Soon matches the
        public ecosystem — no fake Live badges.
      </p>
      {data.categories.map((cat) => {
        const providers = data.providers.filter((p) => p.category === cat.id);
        if (!providers.length) return null;
        return (
          <section key={cat.id} aria-labelledby={`int-cat-${cat.id}`}>
            <div className="mb-3">
              <h3
                id={`int-cat-${cat.id}`}
                className="text-sm font-semibold tracking-tight text-foreground"
              >
                {cat.name}
              </h3>
              <p className="mt-0.5 text-[12px] text-muted-foreground">{cat.description}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {providers.map((p) => (
                <IntegrationCard
                  key={p.id}
                  provider={p}
                  onChanged={() => {
                    void qc.invalidateQueries({ queryKey: ["integrations-catalog"] });
                    void qc.invalidateQueries({ queryKey: ["library-connections"] });
                  }}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
