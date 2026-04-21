// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

import { Delta, YFile } from '../src';

describe('@jupyter/ydoc', () => {
  describe('YFile', () => {
    describe('#constructor', () => {
      test('should create a document without arguments', () => {
        const file = new YFile();
        expect(file.source.length).toBe(0);
        expect(file.dirty).toBe(false);
        file.dispose();
      });
    });

    describe('#disposed', () => {
      test('should be emitted when the document is disposed', () => {
        const file = new YFile();
        let disposed = false;
        file.disposed.connect(() => {
          disposed = true;
        });
        file.dispose();
        expect(disposed).toEqual(true);
      });
    });

    describe('source', () => {
      test('should set source', () => {
        const file = new YFile();

        const source = 'foo';
        file.source = source;

        expect(file.source).toEqual(source);
        expect(file.dirty).toEqual(false);
        file.dispose();
      });

      test('should get source', () => {
        const file = new YFile();

        const source = 'foo';
        file.source = source;

        expect(file.source).toEqual(source);
        file.dispose();
      });

      test('should update source', () => {
        const file = new YFile();

        const source = 'fooo bar';
        file.source = source;
        expect(file.source).toBe(source);
        expect(file.dirty).toEqual(false);

        file.updateSource(3, 5, '/');
        expect(file.source).toBe('foo/bar');
        expect(file.dirty).toEqual(true);
        file.dispose();
      });

      test('should emit an insert source change', () => {
        const file = new YFile();
        expect(file.source).toBe('');

        const changes: Delta<string>[] = [];
        file.changed.connect((_, c) => {
          changes.push(c.sourceChange!);
        });
        const source = 'foo';
        file.source = source;

        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          [
            {
              insert: 'foo'
            }
          ]
        ]);

        file.dispose();
      });

      test('should emit a delete source change', () => {
        const file = new YFile();
        const source = 'foo';
        file.source = source;
        expect(file.source).toBe(source);

        const changes: Delta<string>[] = [];
        file.changed.connect((_, c) => {
          changes.push(c.sourceChange!);
        });
        file.source = '';

        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          [
            {
              delete: 3
            }
          ]
        ]);

        file.dispose();
      });

      test('should emit an update source change', () => {
        const file = new YFile();
        const source1 = 'foo';
        file.source = source1;
        expect(file.source).toBe(source1);

        const changes: Delta<string>[] = [];
        file.changed.connect((_, c) => {
          changes.push(c.sourceChange!);
        });
        const source = 'bar';
        file.source = source;

        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          [
            {
              delete: 3
            },
            {
              insert: source
            }
          ]
        ]);

        file.dispose();
      });
    });
  });
});
