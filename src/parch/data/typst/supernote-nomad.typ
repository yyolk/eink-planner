#let page-width = 118.87mm
#let page-height = 158.5mm
#let toolbar-clearance = 8mm
#let writing-clearance = 4mm
#let mos-width = 8mm
#let page-margin(side) = (
  top: toolbar-clearance,
  bottom: 0mm,
  left: if side == right { writing-clearance } else { 0mm },
  right: if side == left { writing-clearance } else { 0mm },
)
