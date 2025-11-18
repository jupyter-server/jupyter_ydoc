/*
 * Copyright (c) Jupyter Development Team.
 * Distributed under the terms of the Modified BSD License.
 */

import { YNotebook } from '@jupyter/ydoc'
import { WebsocketProvider } from 'y-websocket'
import ws from 'ws'

const port = process.argv[2]
const notebook = new YNotebook()

const wsProvider = new WebsocketProvider(
  `ws://127.0.0.1:${port}`, 'my-roomname',
  notebook.ydoc,
  { WebSocketPolyfill: ws }
)

wsProvider.on('status', event => {
  console.log(event.status)
})

notebook.changed.connect(() => {
  const cell = notebook.getCell(0)
  if (cell) {
    const youtput = cell.youtputs.get(0)
    const text = youtput.get('text')
    if (text.toString() === 'Hello,') {
      text.insert(6, ' World!')
    }
  }
})
