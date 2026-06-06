/**
 * vClickOutside — Vue custom directive that fires a callback when the user
 * clicks outside the element it is applied to.
 *
 * Usage (in <script setup>):
 *   import { vClickOutside } from '@composables/useClickOutside'
 *
 * Usage (in template):
 *   <div v-click-outside="() => open = false">...</div>
 */
export const vClickOutside = {
  mounted(el: any, binding: any) {
    el._clickOutsideHandler = (event: Event) => {
      if (!el.contains(event.target)) {
        binding.value(event)
      }
    }
    document.addEventListener('click', el._clickOutsideHandler)
  },
  unmounted(el: any) {
    document.removeEventListener('click', el._clickOutsideHandler)
  },
}
