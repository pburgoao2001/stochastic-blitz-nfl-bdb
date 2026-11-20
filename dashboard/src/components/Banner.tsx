export default function Banner({ mock }: { mock: boolean }) {
  if (!mock) return null
  return (
    <div className="bg-yellow-300 text-yellow-900 text-center text-sm font-semibold py-1.5">
      ⚠ datos de prueba
    </div>
  )
}
