/*
 * Copyright (c) Jupyter Development Team.
 * Distributed under the terms of the Modified BSD License.
 */

const esModules = ['lib0', 'y-protocols', 'y-websocket', 'yjs'].join('|');

module.exports = {
  testEnvironment: 'node',
  testRegex: 'lib/test/.*.spec.js[x]?$',

};
