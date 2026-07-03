type PagePlaceholderProps = {
  title: string;
  description: string;
};

export function PagePlaceholder({ title, description }: PagePlaceholderProps) {
  return (
    <section className="rounded border border-slate-200 bg-white p-6">
      <p className="text-xs font-semibold uppercase text-brand-dark">
        Placeholder da issue #272
      </p>
      <h1 className="mt-2 text-2xl font-semibold text-slate-950">{title}</h1>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
        {description} A chamada real da API fica fora do escopo desta issue.
      </p>
    </section>
  );
}
