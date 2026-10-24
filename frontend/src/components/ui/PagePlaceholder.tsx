export default function PagePlaceholder({ title, description }: { title: string; description: string }) {
  return (
    <section className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 text-sm text-slate-500">{description}</p>
    </section>
  )
}
