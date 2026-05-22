import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useCreateProject, type ProjectFilters } from "@/api/projects"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  COUNTRIES,
  REGIONS,
  SUBREGIONS,
  PROPERTY_TYPES,
  ROOM_TYPES,
  TRANSACTION_TYPES,
} from "@/lib/constants"

type Country = "si" | "hr"

export function ProjectCreateDialog() {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [country, setCountry] = useState<Country>("si")
  const [transaction, setTransaction] = useState("prodaja")
  const [region, setRegion] = useState("")
  const [subRegion, setSubRegion] = useState("")
  const [propertyType, setPropertyType] = useState("stanovanje")
  const [rooms, setRooms] = useState<string[]>([])
  const [priceFrom, setPriceFrom] = useState("")
  const [priceTo, setPriceTo] = useState("")
  const [sizeFrom, setSizeFrom] = useState("")
  const [sizeTo, setSizeTo] = useState("")
  const [yearFrom, setYearFrom] = useState("")
  const [yearTo, setYearTo] = useState("")
  const [error, setError] = useState("")

  const createProject = useCreateProject()
  const navigate = useNavigate()

  const countryRegions = REGIONS[country] || {}
  const countrySubregions = SUBREGIONS[country] || {}
  const subRegions = region ? countrySubregions[region] || {} : {}
  const hasSubRegions = Object.keys(countrySubregions).length > 0
  const showRooms = propertyType === "stanovanje"

  const handleCountryChange = (value: string) => {
    const next = (value === "hr" ? "hr" : "si") as Country
    setCountry(next)
    setRegion("")
    setSubRegion("")
  }

  const handleRoomToggle = (room: string) => {
    setRooms((prev) =>
      prev.includes(room) ? prev.filter((r) => r !== room) : [...prev, room]
    )
  }

  const handleSubmit = async () => {
    if (!name || !region) {
      setError("Name and region are required")
      return
    }

    const filters: ProjectFilters = {
      country,
      transaction,
      region,
      sub_region: hasSubRegions ? subRegion || null : null,
      property_type: propertyType,
      rooms: showRooms && rooms.length > 0 ? rooms : null,
      price_from: priceFrom ? Number(priceFrom) : null,
      price_to: priceTo ? Number(priceTo) : null,
      size_from: sizeFrom ? Number(sizeFrom) : null,
      size_to: sizeTo ? Number(sizeTo) : null,
      year_from: yearFrom ? Number(yearFrom) : null,
      year_to: yearTo ? Number(yearTo) : null,
    }

    try {
      const project = await createProject.mutateAsync({ name, filters })
      setOpen(false)
      navigate(`/projects/${project.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create project")
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button />}>
        New Project
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Project</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My search" />
          </div>

          <div className="space-y-2">
            <Label>Country</Label>
            <select
              className="w-full rounded-md border px-3 py-2 text-sm"
              value={country}
              onChange={(e) => handleCountryChange(e.target.value)}
            >
              {Object.entries(COUNTRIES).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Transaction</Label>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={transaction}
                onChange={(e) => setTransaction(e.target.value)}
              >
                {TRANSACTION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Property Type</Label>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={propertyType}
                onChange={(e) => {
                  setPropertyType(e.target.value)
                  if (e.target.value !== "stanovanje") setRooms([])
                }}
              >
                {Object.entries(PROPERTY_TYPES).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          </div>

          {hasSubRegions ? (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Region</Label>
                <select
                  className="w-full rounded-md border px-3 py-2 text-sm"
                  value={region}
                  onChange={(e) => {
                    setRegion(e.target.value)
                    setSubRegion("")
                  }}
                >
                  <option value="">Select region...</option>
                  {Object.entries(countryRegions).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label>Sub-region (optional)</Label>
                <select
                  className="w-full rounded-md border px-3 py-2 text-sm"
                  value={subRegion}
                  onChange={(e) => setSubRegion(e.target.value)}
                  disabled={!region}
                >
                  <option value="">All</option>
                  {Object.entries(subRegions).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <Label>Region</Label>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
              >
                <option value="">Select region...</option>
                {Object.entries(countryRegions).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          )}

          {showRooms && (
            <div className="space-y-2">
              <Label>Rooms</Label>
              <div className="flex flex-wrap gap-2">
                {ROOM_TYPES.map((room) => (
                  <button
                    key={room}
                    type="button"
                    onClick={() => handleRoomToggle(room)}
                    className={`rounded-full border px-3 py-1 text-xs ${
                      rooms.includes(room)
                        ? "border-primary bg-primary text-primary-foreground"
                        : "hover:bg-muted"
                    }`}
                  >
                    {room}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Price from (EUR)</Label>
              <Input type="number" value={priceFrom} onChange={(e) => setPriceFrom(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Price to (EUR)</Label>
              <Input type="number" value={priceTo} onChange={(e) => setPriceTo(e.target.value)} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Size from (m2)</Label>
              <Input type="number" value={sizeFrom} onChange={(e) => setSizeFrom(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Size to (m2)</Label>
              <Input type="number" value={sizeTo} onChange={(e) => setSizeTo(e.target.value)} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Year from</Label>
              <Input type="number" value={yearFrom} onChange={(e) => setYearFrom(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Year to</Label>
              <Input type="number" value={yearTo} onChange={(e) => setYearTo(e.target.value)} />
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button className="w-full" onClick={handleSubmit} disabled={createProject.isPending}>
            {createProject.isPending ? "Creating..." : "Create Project"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
