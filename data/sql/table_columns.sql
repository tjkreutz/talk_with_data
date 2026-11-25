SELECT t.table_type, c.column_name, c.data_type
FROM information_schema.tables t
JOIN information_schema.columns c USING (table_schema, table_name)
WHERE t.table_name = ?
ORDER BY c.ordinal_position
