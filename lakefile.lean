import Lake
open Lake DSL

package external_api where

@[default_target]
lean_lib ExternalAPI where

lean_lib «LeanCopilot» where
  srcDir := "."

require batteries from git "https://github.com/leanprover-community/batteries.git" @ "6e89c7370ca3a91b7d1f29ef7d727a9d027d7b0d"
