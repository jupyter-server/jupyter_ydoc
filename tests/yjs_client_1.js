/*
 * Copyright (c) Jupyter Development Team.
 * Distributed under the terms of the Modified BSD License.
 */

import { YNotebook } from '@jupyter/ydoc'
import { WebsocketProvider } from 'y-websocket'
import ws from 'ws'

const notebook = new YNotebook()

const wsProvider = new WebsocketProvider(
  'ws://localhost:1234', 'my-roomname',
  notebook.ydoc,
  { WebSocketPolyfill: ws }
)

wsProvider.on('sync', (isSynced) => {
  const cell = notebook.getCell(0)
  const youtput = cell.youtputs.get(0)
  const text = youtput.get('text')
  text.insert(1, [' World!'])
})
