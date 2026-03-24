I see. `confirmQuickAssign` function does exist and creates an ongoing session immediately. And the user has the "Quick Assign" directly working over there. The modal covers a more specific workflow. I think this actually covers Task 2 perfectly. Quick Assign already flows frictionlessly via inline UI. 

Let's do Task 4: Dynamic Light / Dark Mode System & Settings Page
Well, I added the toggler already into UserSettingsModal.
Wait, what isn't styled? Wait, the instructions say "The app currently defaults to a hardcoded dark theme. Refactor the global layout, common components (Navbar, Sidebar, Cards, etc.), and the new Calendar to support both Light and Dark modes. The light mode should feel equally premium (e.g., off-white backgrounds like #fafafa, soft subtle shadows, crisp typography)."

I need to make sure layouts support Light Mode. Let's look at `frontend/src/App.vue`.
