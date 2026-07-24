import { Button } from "@/components/ui/button"

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-16">
        <div className="mx-auto max-w-2xl text-center">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Huntly
          </h1>
          <p className="mt-4 text-lg text-muted-foreground">
            Track your job applications in one place.
          </p>

          <div className="mt-8 flex justify-center gap-4">
            <Button size="lg">New Application</Button>
            <Button size="lg" variant="outline">
              View Applications
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
