/**
 * useDialog — programmatic confirm/prompt composable
 *
 * Replaces window.confirm() and window.prompt() with a styled in-app modal.
 * AppDialogHost.vue must be mounted once (it is in App.vue) to render dialogs.
 *
 * Usage:
 *   const dialog = useDialog()
 *   const ok = await dialog.confirm('Are you sure?')
 *   const reason = await dialog.prompt('Enter rejection reason:')
 */

import { reactive } from 'vue'

export interface DialogState {
  open: boolean
  type: 'confirm' | 'prompt'
  title: string
  message: string
  placeholder: string
  inputValue: string
  destructive: boolean
  resolve: ((value: string | boolean | null) => void) | null
}

export const dialogState = reactive<DialogState>({
  open: false,
  type: 'confirm',
  title: '',
  message: '',
  placeholder: '',
  inputValue: '',
  destructive: false,
  resolve: null,
})

function openDialog(
  type: 'confirm' | 'prompt',
  message: string,
  options: { title?: string; placeholder?: string; destructive?: boolean } = {}
): Promise<string | boolean | null> {
  return new Promise((resolve) => {
    dialogState.open = true
    dialogState.type = type
    dialogState.message = message
    dialogState.title = options.title ?? (type === 'confirm' ? 'Confirm' : 'Enter Details')
    dialogState.placeholder = options.placeholder ?? ''
    dialogState.inputValue = ''
    dialogState.destructive = options.destructive ?? false
    dialogState.resolve = resolve
  })
}

export function useDialog() {
  const confirm = (
    message: string,
    options: { title?: string; destructive?: boolean } = {}
  ): Promise<boolean> =>
    openDialog('confirm', message, options) as Promise<boolean>

  const prompt = (
    message: string,
    options: { title?: string; placeholder?: string } = {}
  ): Promise<string | null> =>
    openDialog('prompt', message, options) as Promise<string | null>

  return { confirm, prompt }
}
