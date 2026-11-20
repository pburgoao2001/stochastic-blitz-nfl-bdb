export default function Banner({ mock }: { mock: boolean }) {
  if (!mock) return null

  return (
    <div className="sticky top-0 z-50 w-full bg-amber-300 py-2 text-center text-sm font-semibold text-amber-950 shadow-sm" role="status">
      ⚠ datos de prueba
    </div>
  )
}
