local function has_class(classes, name)
  for _, class in ipairs(classes) do
    if class == name then
      return true
    end
  end
  return false
end

local function escape_html(text)
  return text
    :gsub("&", "&amp;")
    :gsub("<", "&lt;")
    :gsub(">", "&gt;")
end

function CodeBlock(block)
  if has_class(block.classes, "mermaid") then
    return pandoc.RawBlock(
      "html",
      '<pre class="mermaid">\n' .. escape_html(block.text) .. "\n</pre>"
    )
  end
  return block
end
