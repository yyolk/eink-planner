#let page-width = 157.48mm
#let page-height = 209.97mm
#let toolbar-clearance = 5mm
#let writing-clearance = 5mm
#let mos-width = 10mm
#let page-margin(side) = (
  top: toolbar-clearance,
  bottom: 0mm,
  left: if side == right { writing-clearance } else { 0mm },
  right: if side == left { writing-clearance } else { 0mm },
)
