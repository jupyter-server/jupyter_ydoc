# Schemas

Yjs is untyped. We must know what each attribute contains at build time and cast its values when accessing them. It is essential to ensure both models use the same schema, so we avoid errors at run time because we cast to the wrong value. For this purpose, in the following sections, we can find the description of the schema used by each model in case we want to extend them to create a custom model.

## YFile

```typescript
{
	"state": YMap<sting, any>,
	"source": YText

}
```

### state:
```typescript
{
	"dirty": bool,
	"path": str
}
```

## YNotebook

```typescript
{
	"state": YMap<sting, any>,
	"meta": YMap<sting, any>,
	"cells": YArray<YMap<string, any>>
}
```

### state:
```typescript
{
	"dirty": bool,
	"path": str
}
```

### meta:
```typescript
{
	"nbformat": number,
	"nbformat_minor": number,
	"metadata": YMap<string, any>
}
```

### cells
```typescript
[
	{// YMap
		"id": str,
		"cell_type": str,
		"source": YText,
		"metadata": YMap<string, any>,
		"execution_count": Int | None,
		"outputs": [] | None,
		"attachments": {} | None
	}
]
```
